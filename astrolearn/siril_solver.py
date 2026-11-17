"""Isolated Siril integration. Catalog access is explicitly local-only."""

import os
import json
from pathlib import Path
import shutil
import subprocess
import time
from tempfile import TemporaryDirectory

import numpy as np
from astropy.io import fits
from astropy.wcs import WCS, Sip
from PIL import Image

from astrolearn.solver import ROOT, AstapSolver, SolveOptions, SolverFailure, fits_calibration, effective_solve_options


def crop_mapping(header_text, left, top, width, height):
    """Translate a native cropped-image WCS to full preview coordinates."""
    mapping = WCS(fits.Header.fromstring(header_text, sep='\n'))
    mapping.wcs.crpix += [left, top]
    if mapping.sip is not None:
        sip = mapping.sip
        mapping.sip = Sip(sip.a, sip.b, sip.ap, sip.bp,
                          sip.crpix+np.array([left, top]))
    header = mapping.to_header(relax=True)
    header['NAXIS'], header['NAXIS1'], header['NAXIS2'] = 2, width, height
    center = mapping.pixel_to_world((width-1)/2,(height-1)/2).icrs
    return header.tostring(sep='\n',padding=False), center


class SirilSolver:
    def __init__(self):
        default = next((ROOT / 'tools' / 'siril').rglob('siril-cli.exe'), None) if os.name == 'nt' else None
        self.executable = Path(os.environ.get('SIRIL_PATH') or default or shutil.which('siril-cli') or ROOT / 'tools/siril/siril-cli')
        self.catalog = Path(os.environ.get('SIRIL_GAIA_CATALOG', str(ROOT / 'resources/siril/gaia_astrometric.dat')))

    def status(self):
        try:
            manifest = json.loads(self.catalog.with_suffix('.dat.json').read_text())
            catalog_ready = self.catalog.stat().st_size == manifest['bytes'] and manifest['bytes'] > 100_000_000
        except (OSError, ValueError, KeyError):
            catalog_ready = False
        ready = self.executable.is_file() and catalog_ready
        return {'name': 'Siril', 'available': ready, 'offline': True,
                'executable_found': self.executable.is_file(), 'database_found': catalog_ready,
                'message': 'Local Gaia solver ready; position and scale hints required.' if ready else 'Install Siril and its local Gaia astrometric catalog.'}

    def solve(self, image: Path, options: SolveOptions, *, timeout_seconds=120):
        if not self.status()['available']:
            raise ValueError(self.status()['message'])
        calibration = fits_calibration(image)
        effective = effective_solve_options(options, calibration)
        if effective.ra_deg is None or effective.fov_deg <= 0:
            raise ValueError('Siril needs RA, DEC and image height, or a calibrated FITS image. Use ASTAP for an unknown field.')
        # Siril's near-search accepts at most 30 degrees. The shared API also
        # supports ASTAP's 180-degree blind search, so record the actual limit.
        radius_warning = ''
        if effective.radius_deg > 30:
            effective = effective.model_copy(update={'radius_deg': 30})
            radius_warning = 'Siril used its maximum 30-degree near-search radius.'
        with TemporaryDirectory(prefix='astrolearn-siril-') as folder:
            work = Path(folder)
            if image.suffix.lower() in {'.fit', '.fits', '.fts'}:
                array = fits.getdata(image)
            else:
                with Image.open(image) as raster:
                    array = np.asarray(raster.convert('L'))
            # Fresh input has no existing WCS to accidentally accept as a solve.
            fits.writeto(work / 'input.fits', array)
            pixel_scale = effective.fov_deg * 3600 / array.shape[0]
            # A virtual 1-micron pixel expresses the supplied angular scale.
            # This is numerical solver input, not a claim about camera hardware.
            focal = 206.264806247 / pixel_scale
            catalog = self.catalog.resolve().as_posix()
            if any(c in catalog for c in ['"', '\n', '\r']):
                raise ValueError('Unsupported catalog path.')
            script = '\n'.join([
                'requires 1.4.0', f'set "core.catalogue_gaia_astro={catalog}"',
                'load input.fits',
                f'platesolve {effective.ra_deg},{effective.dec_deg} -focal={focal} -pixelsize=1 -catalog=localgaia -noflip -force -radius={effective.radius_deg}',
                'save solved.fit', 'close', ''])
            (work / 'solve.ssf').write_text(script, encoding='utf-8')
            # Siril requires an existing config for -i. Empty INI uses defaults
            # without reading or overwriting the user's interactive settings.
            (work / 'settings.cfg').write_text('', encoding='utf-8')
            result = subprocess.run([str(self.executable.resolve()), '--offline', '-i', str(work / 'settings.cfg'), '-d', str(work), '-s', str(work / 'solve.ssf')],
                                    capture_output=True, text=True, errors='replace', timeout=timeout_seconds,
                                    env={**os.environ, 'PIP_NO_INDEX': '1', 'PIP_DISABLE_PIP_VERSION_CHECK': '1', 'UV_OFFLINE': '1'},
                                    creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
            log = result.stdout + result.stderr
            output = work / 'solved.fit'
            if result.returncode or not output.is_file():
                raise SolverFailure('Siril did not find a verified star-pattern solution.', log)
            header = fits.getheader(output)
            mapping = WCS(header).celestial
            if not mapping.has_celestial or not np.isfinite(mapping.pixel_scale_matrix).all():
                raise SolverFailure('Siril returned no valid celestial mapping.', log)
            center = mapping.pixel_to_world((array.shape[1] - 1) / 2, (array.shape[0] - 1) / 2).icrs
            scale = np.sqrt(abs(np.linalg.det(mapping.pixel_scale_matrix))) * 3600
            return {'ra_deg': float(center.ra.deg), 'dec_deg': float(center.dec.deg),
                    'pixel_scale_arcsec': float(scale), 'rotation_deg': float(np.degrees(np.arctan2(mapping.pixel_scale_matrix[1, 0], mapping.pixel_scale_matrix[1, 1]))),
                    'solver': 'Siril / local Gaia DR3', 'frame': 'ICRS/J2000',
                    'wcs_header': header.tostring(sep='\n', padding=False),
                    'effective_options': effective.model_dump(), 'input_calibration': calibration,
                    'pixel_convention': 'zero-based preview column x, row y', 'warning': radius_warning}


class LocalSolvers:
    """Choose installed offline engines, retaining failures if neither succeeds."""
    def __init__(self):
        self.astap = AstapSolver()
        self.siril = SirilSolver()

    def status(self):
        primary = self.astap.status()
        other = self.siril.status()
        return {**primary, 'name': 'Local solvers', 'available': primary['available'] or other['available'],
                'backends': [primary, other]}

    def solve(self, image, options):
        if options.backend != 'auto':
            return getattr(self, options.backend).solve(image, options)
        effective = effective_solve_options(options, fits_calibration(image))
        eligible = self.siril.status()['available'] and effective.ra_deg is not None and effective.fov_deg > 0
        engines = [self.siril, self.astap] if eligible else [self.astap]
        logs = []
        for engine in engines:
            # Unknown raster scales need more than ASTAP's limited automatic
            # range. Try explicit scale hypotheses against actual star patterns,
            # within a shared two-minute budget. These are search trials, never
            # accepted coordinates or assumptions about the user's camera.
            if engine is self.astap and effective.fov_deg == 0:
                deadline = time.monotonic() + 120
                for height, budget in ((2, 25), (8, 20), (40, 15), (20, 15), (70, 15), (0, 30)):
                    remaining = deadline-time.monotonic()
                    if remaining <= 0:
                        break
                    trial = options.model_copy(update={'fov_deg': height})
                    try:
                        solution = engine.solve(image, trial, timeout_seconds=min(budget, remaining))
                        solution['previous_attempts'] = logs
                        solution['scale_search'] = 'bounded automatic scale trials'
                        return solution
                    except (ValueError, subprocess.TimeoutExpired) as exc:
                        logs.append(f"ASTAP image height {height} deg: {exc}\n{getattr(exc, 'log', '')}")
                continue
            try:
                solution = engine.solve(image, options)
                solution['previous_attempts'] = logs
                return solution
            except (ValueError, subprocess.TimeoutExpired) as exc:
                logs.append(f"{engine.status()['name']}: {exc}\n{getattr(exc, 'log', '')}")
        # An extended bright nebula can spoil full-frame star extraction. With
        # actual pointing/scale hints, try independent corner crops and translate
        # the native WCS back to original pixels. Never reuse a prior image WCS.
        if eligible:
            if image.suffix.lower() in {'.fit', '.fits', '.fts'}:
                array = fits.getdata(image)
            else:
                with Image.open(image) as raster:
                    array = np.asarray(raster.convert('L'))
            height, width = array.shape
            ch, cw = height//2, width//2
            if min(ch, cw) >= 256:
                for left, top in ((0, 0), (width-cw, height-ch)):
                    with TemporaryDirectory(prefix='astrolearn-crop-') as folder:
                        cropped = Path(folder)/'crop.fits'
                        fits.writeto(cropped, array[top:top+ch,left:left+cw])
                        trial = effective.model_copy(update={'fov_deg': effective.fov_deg*ch/height})
                        try:
                            solution = self.siril.solve(cropped, trial, timeout_seconds=30)
                            header_text, center = crop_mapping(solution['wcs_header'],left,top,width,height)
                            solution.update(ra_deg=float(center.ra.deg), dec_deg=float(center.dec.deg),
                                wcs_header=header_text,
                                solved_region={'left':left,'top':top,'width':cw,'height':ch},
                                previous_attempts=logs,
                                warning='Matched stars in one part of the image. Positions elsewhere may be less accurate.')
                            return solution
                        except (ValueError, subprocess.TimeoutExpired) as exc:
                            logs.append(f"Corner crop {left},{top}: {exc}\n{getattr(exc, 'log', '')}")
        if any('Not enough stars' in entry for entry in logs):
            message = 'Not enough usable stars to solve this photo. Try the original higher-resolution image.'
        elif any('timed out' in entry for entry in logs):
            message = "Star search timed out. Add the image's field of view in Image settings and retry."
        else:
            message = 'No matching star pattern found. Add the field of view in Image settings or try the original higher-resolution image.'
        raise SolverFailure(message, '\n\n'.join(logs))
