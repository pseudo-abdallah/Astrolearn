"""Image prototype orchestration: APIs stay responsive while ASTAP works."""

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
from threading import Lock

from astropy import units as u
from astropy.coordinates import SkyCoord
from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel, ConfigDict, Field
from starlette.concurrency import run_in_threadpool

from astrolearn.astronomy import SiteRequest, catalog, position
from astrolearn.imaging import MAX_BYTES, decode_image, detect_sources
from astrolearn.mount import MoveRequest, SimulatedMount
from astrolearn.prototype_store import PrototypeStore
from astrolearn.solver import AstapSolver, SolveOptions, SolverFailure, fits_calibration
from astrolearn.identification import OfflineIdentifier
from astrolearn.siril_solver import LocalSolvers


class SessionRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    image_id: str
    solve_id: str | None = None
    site: SiteRequest
    notes: str = Field(default='', max_length=4000)


class Prototype:
    def __init__(self, db_path: Path, solver=None):
        self.store = PrototypeStore(db_path)
        self.solver = solver or LocalSolvers()
        self.identifier = OfflineIdentifier()
        self.mount = SimulatedMount()
        self.lock = Lock()
        self.executor = None

    def start(self):
        self.store.initialize()
        self.executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix='plate-solve')

    def close(self):
        # Each job has a 120-second subprocess timeout and persists its outcome.
        self.executor.shutdown(wait=True, cancel_futures=True)

    def require(self, kind, key):
        record = self.store.get(kind, key)
        if record is None:
            raise HTTPException(404, f'{kind.capitalize()} not found')
        return record

    def solve_worker(self, job, image, options):
        try:
            job.update(status='running', message='Matching stars against the local catalog…')
            self.store.save('solve', job)
            if image['analysis'].get('analysis_version', 1) < 3:
                rgb, _, _ = decode_image((self.store.files / image['original']).read_bytes())
                image['analysis'] = detect_sources(rgb)
                self.store.save('image', image)
            solution = self.solver.solve(self.store.files / image['original'], options)
            job.update(status='solved', solution=solution, message='Field solved locally.')
            # Identification is a separate stage: a missing catalog or mapping
            # must not turn a valid plate solution into a fabricated identity.
            try:
                job['identification'] = self.identifier.identify(solution, image['analysis'])
                job['message'] = 'Field solved and catalog matching completed locally.'
            except (ValueError, OSError, KeyError) as exc:
                job['identification'] = {'status': 'unavailable', 'message': str(exc), 'offline': True}
        except subprocess.TimeoutExpired:
            job.update(status='failed', message='Solve timed out after 120 seconds. Check field of view and hints.')
        except SolverFailure as exc:
            job.update(status='failed', message=str(exc), solver_log=exc.log)
        except (ValueError, OSError, KeyError) as exc:
            job.update(status='failed', message=str(exc))
        except Exception:
            # Avoid leaking traceback or a permanently running job to the UI.
            import logging
            logging.getLogger(__name__).exception('Unexpected plate solver failure')
            job.update(status='failed', message='Unexpected solver failure. Check the server log.')
        finally:
            try:
                job['finished_at'] = datetime.now(timezone.utc).isoformat()
                self.store.save('solve', job)
            finally:
                self.lock.release()

    def router(self):
        router = APIRouter(prefix='/api/v1')

        @router.get('/prototype/status')
        def status():
            return {'mode': 'image-only prototype', 'location_source': 'manual',
                    'camera': 'not configured', 'mount': self.mount.status(),
                    'solver': self.solver.status(), 'catalog_count': len(catalog()),
                    'identification': self.identifier.status()}

        @router.get('/catalog')
        def targets():
            return catalog()

        @router.post('/astronomy/position')
        def target_position(item: SiteRequest):
            try:
                return position(item)
            except ValueError as exc:
                raise HTTPException(422, str(exc)) from exc

        @router.post('/images', status_code=201)
        async def upload(request: Request):
            # Stream a bounded raw request: no filename paths or multipart parser needed.
            data = bytearray()
            async for chunk in request.stream():
                data.extend(chunk)
                if len(data) > MAX_BYTES:
                    raise HTTPException(413, 'Image exceeds 20 MB.')
            def process():
                try:
                    rgb, preview, extension = decode_image(bytes(data))
                    analysis = detect_sources(rgb)
                except (ValueError, OSError) as exc:
                    raise HTTPException(422, str(exc)) from exc
                from uuid import uuid4
                key = uuid4().hex
                original = key + extension
                display = key + '-preview.png'
                # Originals are retained for repeatable solves, not altered by overlays.
                (self.store.files / original).write_bytes(bytes(data) if extension == '.fits' else preview)
                (self.store.files / display).write_bytes(preview)
                return self.store.save('image', {'id': key, 'created_at': datetime.now(timezone.utc).isoformat(),
                    'original': original, 'preview': display, 'analysis': analysis,
                    'calibration': fits_calibration(self.store.files / original),
                    'preview_url': f'/api/v1/images/{key}/preview', 'original_url': f'/api/v1/images/{key}/original'})
            return await run_in_threadpool(process)

        @router.get('/images')
        def images(limit: int = Query(50, ge=1, le=100), offset: int = Query(0, ge=0)):
            return self.store.list('image', limit, offset)

        @router.get('/images/{image_id}')
        def image_metadata(image_id: str):
            return self.require('image', image_id)

        @router.get('/images/{image_id}/sources')
        def image_sources(image_id: str):
            image = self.require('image', image_id)
            if image['analysis'].get('analysis_version', 1) < 3:
                rgb, _, _ = decode_image((self.store.files/image['original']).read_bytes())
                image['analysis'] = detect_sources(rgb)
                self.store.save('image', image)
            return image['analysis']

        @router.get('/images/{image_id}/latest-solve')
        def latest_solve(image_id: str):
            self.require('image', image_id)
            return self.store.latest_for_image('solve', image_id)

        @router.get('/solves/{solve_id}/wcs')
        def download_wcs(solve_id: str):
            job = self.require('solve', solve_id)
            solution = job.get('solution') or {}
            if job['status'] != 'solved' or not solution.get('wcs_header'):
                raise HTTPException(404, 'This solve has no saved WCS mapping. Solve the image again.')
            return Response(solution['wcs_header'], media_type='text/plain',
                            headers={'Content-Disposition': f'attachment; filename="astrolearn-{job["id"]}.wcs.txt"'})

        @router.get('/images/{image_id}/preview')
        def preview(image_id: str):
            image = self.require('image', image_id)
            return FileResponse(self.store.files / image['preview'], media_type='image/png')

        @router.get('/images/{image_id}/original')
        def original(image_id: str):
            image = self.require('image', image_id)
            return FileResponse(self.store.files / image['original'], filename=image['original'])

        @router.post('/images/{image_id}/solve', status_code=202)
        def solve(image_id: str, options: SolveOptions):
            image = self.require('image', image_id)
            if not self.solver.status()['available']:
                raise HTTPException(503, 'Install an offline solver and its star database first. See README.')
            if not self.lock.acquire(blocking=False):
                raise HTTPException(409, 'A solve is already running. Wait for it to finish.')
            try:
                advice = []
                width, height = image['analysis']['width'], image['analysis']['height']
                if width < 960 or height < 960:
                    advice.append(f'Small image ({width} × {height} pixels). Prefer the original full-resolution image or FITS file. Enlarging a thumbnail does not recover detail.')
                calibration = image.get('calibration')
                if calibration:
                    advice.append('This FITS image has calibration metadata. Missing scale/position hints are read from its header; ASTAP still must verify the actual star pattern.')
                if options.fov_deg == 0 and not calibration:
                    advice.append('Automatic image height is a limited scale search, not every possible field of view. Supply the true image height in degrees if known; pixels are not degrees.')
                if options.ra_deg is None and not calibration:
                    advice.append('No coordinate hint was supplied. If the source identifies the target, use its coordinates as a search hint; a hint is not a verified result.')
                databases = self.solver.status().get('databases', [])
                if databases:
                    smallest = min(databases, key=lambda d: d['min_fov_deg'])
                    advice.append(f"Installed catalogs reach approximately {smallest['min_fov_deg']}° image height ({smallest['name']}). For tighter fields, check for a catalog rated for a smaller field and confirm the true image scale.")
                advice.append('OpenCV circles are bright candidates. ASTAP extracts its own usable stars; a large circle count does not guarantee a solution.')
                job = self.store.new('solve', image_id=image_id, options=options.model_dump(), diagnostics=advice, status='queued', message='Queued', solution=None)
                self.executor.submit(self.solve_worker, dict(job), image, options)
                return job
            except Exception:
                self.lock.release()
                raise

        @router.get('/solves/{solve_id}')
        def solve_status(solve_id: str):
            return self.require('solve', solve_id)

        @router.get('/solves/{solve_id}/log')
        def solve_log(solve_id: str):
            job = self.require('solve', solve_id)
            if not job.get('solver_log'):
                raise HTTPException(404, 'No saved diagnostic log for this attempt.')
            return Response(job['solver_log'], media_type='text/plain',
                            headers={'Content-Disposition': 'attachment; filename="astrolearn-solver.log"'})

        @router.post('/sessions', status_code=201)
        def save_session(item: SessionRequest):
            image = self.require('image', item.image_id)
            try:
                expected = position(item.site)
            except ValueError as exc:
                raise HTTPException(422, str(exc)) from exc
            job = self.require('solve', item.solve_id) if item.solve_id else None
            if job and job['image_id'] != item.image_id:
                raise HTTPException(422, 'The solution belongs to a different image.')
            error = None
            solution = job['solution'] if job and job['status'] == 'solved' else None
            comparison_warning = ''
            if solution:
                if expected['coordinate_frame'] != 'ICRS/J2000':
                    comparison_warning = 'Install local DE421 for solar-system pointing comparison; fallback frame differs.'
                else:
                    a = SkyCoord(expected['ra_deg'] * u.deg, expected['dec_deg'] * u.deg)
                    b = SkyCoord(solution['ra_deg'] * u.deg, solution['dec_deg'] * u.deg)
                    error = float(a.separation(b).deg)
            return self.store.new('session', image_id=image['id'], preview_url=image['preview_url'],
                target=expected['target']['name'], observation_utc=item.site.utc.isoformat(), expected=expected,
                solve_id=item.solve_id, solution=solution, pointing_error_deg=error,
                field_center_within_threshold=error is not None and error < 0.25,
                # A matching field center does not prove physical tracking or object identification.
                tracking_duration_s=0, tracking_status='not available — no physical mount',
                identification=job.get('identification') if job and solution else None,
                solar_analysis=self.store.latest_for_image('solar-analysis', image['id']),
                comparison_warning=comparison_warning, notes=item.notes)

        @router.get('/sessions')
        def sessions(limit: int = Query(50, ge=1, le=100), offset: int = Query(0, ge=0)):
            return self.store.list('session', limit, offset)

        @router.get('/sessions/export')
        def export():
            # Export the complete history, not only the first UI page.
            records, offset = [], 0
            while batch := self.store.list('session', 100, offset):
                records.extend(batch)
                offset += 100
            return Response(json.dumps(records, indent=2), media_type='application/json',
                            headers={'Content-Disposition': 'attachment; filename="astrolearn-observations.json"'})

        @router.get('/mount')
        def mount_status():
            return self.mount.status()

        @router.post('/mount/move')
        def move(command: MoveRequest):
            try:
                return self.mount.move(command)
            except ValueError as exc:
                raise HTTPException(409, str(exc)) from exc

        @router.post('/mount/stop')
        def stop():
            return self.mount.stop()

        @router.post('/mount/reset')
        def reset():
            try:
                return self.mount.reset()
            except ValueError as exc:
                raise HTTPException(409, str(exc)) from exc

        return router
