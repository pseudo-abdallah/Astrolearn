"""One automatic image workflow, preserving distinct forms of evidence."""

from datetime import datetime, timezone
import subprocess

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from astrolearn.astronomy import SiteRequest, position
from astrolearn.imaging import decode_image, detect_sources
from astrolearn.identification import IDENTIFICATION_VERSION
from astrolearn.solar import disk_box, classify_closeup, identify_field
from astrolearn.solver import SolveOptions, SolverFailure

ANALYSIS_VERSION = 3


class AnalysisRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    options: SolveOptions = Field(default_factory=SolveOptions)
    observation: SiteRequest | None = None
    reuse_solution: bool = False


class GoToRequest(SiteRequest):
    client_id: str = Field(min_length=1, max_length=80, pattern=r'^[a-zA-Z0-9-]+$')
    sequence: int = Field(ge=1, strict=True)


def analyze_worker(prototype, job, image, request):
    store = prototype.store
    plate = None
    rgb = None
    resolved = False
    try:
        job.update(status='running', message='Analyzing image…', analysis_version=ANALYSIS_VERSION)
        store.save('analysis', job)
        rgb, _, _ = decode_image((store.files / image['original']).read_bytes())
        if image['analysis'].get('analysis_version', 1) < 3:
            image['analysis'] = detect_sources(rgb)
            store.save('image', image)
        box = disk_box(rgb)
        height, width = rgb.shape[:2]
        outside = 0
        if box:
            x, y, w, h = box
            pad = max(w, h)*.1
            outside = sum(not (x-pad <= s['x'] <= x+w+pad and y-pad <= s['y'] <= y+h+pad)
                          for s in image['analysis']['sources'])
        resolved = not image.get('calibration') and box is not None and outside < 8 and (
            box[2]*box[3] > width*height*.04 or
            (image['analysis']['count'] < 15 and min(box[2:]) >= 16))
        previous = store.successful_solve(image['id']) if request.reuse_solution else None
        if previous and previous['status'] == 'solved':
            plate = previous
            if previous['image_id'] != image['id']:
                # Keep downstream endpoints tied to the selected upload while
                # retaining the exact provenance of the verified mapping.
                plate = store.new('solve', image_id=image['id'], status='solved',
                    solution=previous['solution'], options=previous.get('options'),
                    identification=prototype.identifier.identify(previous['solution'], image['analysis']),
                    reused_from_solve_id=previous['id'],
                    message='Recovered the verified solution for an identical image.')
        else:
            if resolved or image['analysis']['count'] < 3:
                visual = classify_closeup(rgb)
                if visual['status'] == 'suggestion' or image['analysis']['count'] < 3:
                    job.update(solar=visual, kind_result='closeup', status='completed',
                               message='Image analysis complete.')
                    return
            job['message'] = 'Matching the star field…'
            store.save('analysis', job)
            plate = store.new('solve', image_id=image['id'], options=request.options.model_dump(),
                              status='running', message='Automatic star-field solve', solution=None)
            job['solve_id'] = plate['id']
            store.save('analysis', job)
            solution = prototype.solver.solve(store.files / image['original'], request.options)
            plate.update(status='solved', solution=solution, message='Field solved locally.',
                         finished_at=datetime.now(timezone.utc).isoformat())
            try:
                plate['identification'] = prototype.identifier.identify(solution, image['analysis'])
            except (ValueError, OSError, KeyError) as exc:
                plate['identification'] = {'status': 'unavailable', 'message': str(exc)}
            store.save('solve', plate)
        job.update(solve_id=plate['id'], plate=plate, kind_result='field')
        if request.observation:
            try:
                job['solar'] = identify_field(plate['solution'], image['analysis'], request.observation)
            except (ValueError, OSError, KeyError) as exc:
                job['solar_warning'] = str(exc)
        else:
            job['solar_warning'] = 'Add the image capture time in settings to check moving bodies in this field.'
        job.update(status='completed', message='Image analysis complete.')
    except (ValueError, OSError, KeyError, subprocess.TimeoutExpired) as exc:
        if plate and plate['status'] == 'running':
            plate.update(status='failed', message=str(exc), solver_log=getattr(exc, 'log', ''),
                         finished_at=datetime.now(timezone.utc).isoformat())
            store.save('solve', plate)
        job.update(plate=plate, solver_log=getattr(exc, 'log', ''), message=str(exc), field_error=str(exc))
        # A failed star match can still be a recognizable resolved object. It is
        # always a visual suggestion, never promoted to successful astrometry.
        try:
            if rgb is None:
                raise ValueError('Image is unavailable.')
            if resolved:
                job.update(solar=classify_closeup(rgb), kind_result='closeup', status='completed')
            else:
                job.update(kind_result='field', status='failed')
        except (ValueError, OSError, ImportError):
            job['status'] = 'failed'
    except Exception:
        import logging
        logging.getLogger(__name__).exception('Automatic image analysis failed')
        job.update(status='failed', message='Image analysis failed. Try another image.')
        if plate and plate['status'] == 'running':
            plate.update(status='failed', message=job['message'])
            store.save('solve', plate)
    finally:
        try:
            if job.get('solar'):
                solar = job['solar']
                saved = store.new('solar-analysis', image_id=image['id'], solve_id=job.get('solve_id'), **solar)
                job['solar'] = saved
            job['finished_at'] = datetime.now(timezone.utc).isoformat()
            store.save('analysis', job)
        finally:
            prototype.lock.release()


def automatic_router(prototype):
    router = APIRouter(prefix='/api/v1')

    def refresh_names(result, image=None):
        # Apply catalog upgrades to saved WCS without running a new plate solve.
        plate = (result or {}).get('plate') or {}
        if plate.get('status') != 'solved':
            return result
        if (plate.get('identification') or {}).get('identification_version') == IDENTIFICATION_VERSION:
            return result
        image = image or prototype.require('image', result['image_id'])
        try:
            plate['identification'] = prototype.identifier.identify(plate['solution'], image['analysis'])
        except (ValueError, OSError, KeyError):
            return result
        prototype.store.save('analysis', result)
        return result

    @router.post('/images/{image_id}/analyze', status_code=202)
    def analyze(image_id: str, request: AnalysisRequest):
        image = prototype.require('image', image_id)
        if not prototype.lock.acquire(blocking=False):
            raise HTTPException(409, 'Another image is being analyzed. Wait for it to finish.')
        try:
            job = prototype.store.new('analysis', image_id=image_id, status='queued', message='Queued',
                observation=request.observation.model_dump(mode='json') if request.observation else None)
            prototype.executor.submit(analyze_worker, prototype, dict(job), image, request)
            return job
        except Exception:
            prototype.lock.release()
            raise

    @router.get('/analyses/{analysis_id}')
    def analysis(analysis_id: str):
        return refresh_names(prototype.require('analysis', analysis_id))

    @router.get('/images/{image_id}/latest-analysis')
    def latest(image_id: str):
        image = prototype.require('image', image_id)
        return refresh_names(prototype.store.latest_for_image('analysis', image_id), image)

    @router.post('/mount/goto')
    def goto(request: GoToRequest):
        try:
            calculated = position(request)
            mount = prototype.mount.goto(calculated, request.client_id, request.sequence)
            return {'position': calculated, 'mount': mount}
        except ValueError as exc:
            raise HTTPException(409 if 'selection' in str(exc) or 'stopped' in str(exc) else 422, str(exc)) from exc

    return router
