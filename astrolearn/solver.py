"""Real offline ASTAP subprocess adapter; never manufactures a solution."""

import math
import os
from pathlib import Path
import shutil
import subprocess
from typing import Literal
from tempfile import TemporaryDirectory

import numpy as np
from astropy.io import fits
from astropy.wcs import WCS
from PIL import Image
from pydantic import BaseModel, ConfigDict, Field, model_validator

ROOT = Path(__file__).resolve().parent.parent


class SolverFailure(ValueError):
    """Keep native diagnostics after the isolated working directory is removed."""
    def __init__(self, message: str, log: str):
        super().__init__(message)
        self.log = log[-24000:]


class SolveOptions(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    backend: Literal['auto', 'astap', 'siril'] = 'auto'
    fov_deg: float = Field(default=0, ge=0, le=90)
    ra_deg: float | None = Field(default=None, ge=0, lt=360)
    dec_deg: float | None = Field(default=None, ge=-90, le=90)
    radius_deg: float = Field(default=180, gt=0, le=180)

    @model_validator(mode="after")
    def paired_hint(self):
        if (self.ra_deg is None) != (self.dec_deg is None):
            raise ValueError("Supply both RA and DEC hints, or neither.")
        if self.ra_deg is None and self.radius_deg != 180:
            raise ValueError("A restricted search radius requires RA and DEC hints.")
        return self


def parse_solution(text: str) -> dict:
    values = {}
    for line in text.splitlines():
        if '=' in line:
            key, value = line.split('=', 1)
            values[key.strip().upper()] = value.split('//', 1)[0].strip().strip("'")
    if values.get('PLTSOLVD') != 'T':
        raise ValueError("No plate solution found. Try another star field or adjust field of view.")
    ra, dec = float(values['CRVAL1']), float(values['CRVAL2'])
    scale = abs(float(values['CDELT2'])) * 3600
    rotation = float(values.get('CROTA2', 0))
    if not all(math.isfinite(v) for v in (ra, dec, scale, rotation)) or not (0 <= ra < 360 and -90 <= dec <= 90 and scale > 0):
        raise ValueError("Solver returned invalid coordinates.")
    return {"ra_deg": ra, "dec_deg": dec, "pixel_scale_arcsec": scale,
            "rotation_deg": rotation, "frame": "ICRS/J2000", "solver": "ASTAP",
            "warning": values.get('WARNING', '')}


def fits_calibration(image: Path) -> dict | None:
    """Read initial search hints from a FITS WCS; never return a plate solution.

    A header can be inaccurate. ASTAP must still match the actual pixel pattern.
    Raster thumbnails have no equivalent calibration and receive no guessed scale.
    """
    if image.suffix.lower() not in {'.fits', '.fit', '.fts'}:
        return None
    try:
        header = fits.getheader(image)
        if header.get('NAXIS') != 2 or not header.get('CTYPE1') or not header.get('CTYPE2'):
            return None
        mapping = WCS(header).celestial
        if not mapping.has_celestial:
            return None
        width, height = header['NAXIS1'], header['NAXIS2']
        center = mapping.pixel_to_world((width - 1) / 2, (height - 1) / 2).icrs
        bottom = mapping.pixel_to_world((width - 1) / 2, -0.5)
        top = mapping.pixel_to_world((width - 1) / 2, height - 0.5)
        fov = float(bottom.separation(top).deg)
        ra, dec = float(center.ra.deg), float(center.dec.deg)
        if not all(math.isfinite(value) for value in (ra, dec, fov)) or not (0 < fov <= 90):
            return None
        return {'ra_deg': ra, 'dec_deg': dec, 'fov_deg': fov,
                'source': 'FITS WCS header; unverified search hints'}
    except (ValueError, TypeError, KeyError, OSError, IndexError):
        return None


def effective_solve_options(options: SolveOptions, calibration: dict | None) -> SolveOptions:
    values = options.model_dump()
    if calibration:
        if values['fov_deg'] == 0:
            values['fov_deg'] = calibration['fov_deg']
        if values['ra_deg'] is None:
            values['ra_deg'] = calibration['ra_deg']
            values['dec_deg'] = calibration['dec_deg']
    return SolveOptions(**values)


class AstapSolver:
    def __init__(self):
        default = ROOT / 'tools' / 'astap' / ('astap_cli.exe' if os.name == 'nt' else 'astap_cli')
        if not default.is_file() and (default.parent / ('astap.exe' if os.name == 'nt' else 'astap')).is_file():
            default = default.parent / ('astap.exe' if os.name == 'nt' else 'astap')
        self.executable = Path(os.environ.get('ASTAP_PATH', str(default))).resolve()
        self.database = Path(os.environ.get('ASTAP_DATABASE', str(default.parent))).resolve()

    def status(self):
        catalogs = [p.name for pattern in ('*.1476', '*.290', '*.001') for p in self.database.glob(pattern)]
        # Report resource coverage, not merely whether any star file exists.
        ranges = {'d80': (0.15, 6), 'd50': (0.2, 6), 'd20': (0.3, 6),
                  'd05': (0.6, 6), 'g05': (3, 20), 'w08': (20, 80)}
        installed = [{'name': name.upper(), 'min_fov_deg': bounds[0], 'max_fov_deg': bounds[1]}
                     for name, bounds in ranges.items() if any(p.lower().startswith(name + '_') for p in catalogs)]
        return {"name": "ASTAP", "offline": True, "available": self.executable.is_file() and bool(catalogs),
                "executable_found": self.executable.is_file(), "database_found": bool(catalogs),
                "databases": installed,
                "message": "Ready for local solving" if self.executable.is_file() and catalogs else "Install ASTAP and a matching star database; see README."}

    def solve(self, image: Path, options: SolveOptions, *, timeout_seconds=120) -> dict:
        if not self.status()['available']:
            raise ValueError("Offline solver is not installed with its star database.")
        calibration = fits_calibration(image)
        effective = effective_solve_options(options, calibration)
        # Unique working directory prevents stale WCS files and cross-job contamination.
        with TemporaryDirectory(prefix='astrolearn-solve-') as folder:
            work = Path(folder)
            source = work / 'input.fits'
            if image.suffix.lower() in {'.fits', '.fit', '.fts'}:
                shutil.copyfile(image, source)
            else:
                # Give ASTAP exactly the array shown by the preview. A FITS input
                # avoids ambiguous PNG/JPEG bottom-up conventions: WCS (x,y)
                # maps to preview column x and row y, both zero-based.
                with Image.open(image) as raster:
                    fits.PrimaryHDU(np.asarray(raster.convert('L'))).writeto(source)
            output = work / 'solution'
            command = [str(self.executable), '-f', str(source), '-o', str(output),
                       '-d', str(self.database), '-fov', str(effective.fov_deg),
                       '-r', str(effective.radius_deg), '-z', '0', '-wcs', '-log',
                       # Pin documented defaults instead of inheriting GUI settings.
                       '-s', '500', '-t', '0.007', '-m', '1.5', '-speed', 'auto',
                       '-ra', str((effective.ra_deg or 0) / 15),
                       '-spd', str((effective.dec_deg or 0) + 90)]
            # No shell; numeric options are validated. Timeout kills the solver.
            try:
                result = subprocess.run(command, capture_output=True, text=True, timeout=timeout_seconds,
                                        creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
            except subprocess.TimeoutExpired as exc:
                # Read diagnostics before TemporaryDirectory removes them. A
                # timeout otherwise erased the native star count and catalog,
                # making search-budget failures look like poor source detection.
                log_file = output.with_suffix('.log')
                if log_file.is_file():
                    log = log_file.read_text(encoding='utf-8', errors='replace')
                else:
                    def decoded(value):
                        return value.decode('utf-8',errors='replace') if isinstance(value,bytes) else value or ''
                    log = decoded(exc.stdout)+decoded(exc.stderr)
                raise SolverFailure(f'ASTAP search timed out after {timeout_seconds:g} seconds.', log) from exc
            errors = {1: 'No solution. Check the field of view and star database.',
                      2: 'Not enough stars detected to solve this image.',
                      16: 'ASTAP could not read this image.', 32: 'No matching star database found.',
                      33: 'ASTAP could not read the star database.'}
            if result.returncode:
                log_file = output.with_suffix('.log')
                log = log_file.read_text(encoding='utf-8', errors='replace') if log_file.is_file() else result.stdout + result.stderr
                # The log is a local diagnostic, never interpreted as a solution.
                raise SolverFailure(errors.get(result.returncode, f'ASTAP failed with code {result.returncode}.'), log)
            ini = output.with_suffix('.ini')
            if not ini.is_file():
                raise ValueError('ASTAP did not produce a solution file.')
            solution = parse_solution(ini.read_text(encoding='utf-8', errors='replace'))
            solution['effective_options'] = effective.model_dump()
            solution['input_calibration'] = calibration
            wcs_path = output.with_suffix('.wcs')
            if wcs_path.is_file():
                header = fits.Header.fromfile(wcs_path)
                shape = fits.getdata(source).shape
                header['NAXIS'] = 2
                header['NAXIS1'] = shape[1]
                header['NAXIS2'] = shape[0]
                celestial = WCS(header).celestial
                if not celestial.has_celestial or not np.isfinite(celestial.pixel_scale_matrix).all():
                    raise ValueError('ASTAP returned an invalid celestial image mapping.')
                # Keep the actual full header, including projection and distortion
                # coefficients, before the temporary solver directory is removed.
                solution['wcs_header'] = header.tostring(sep='\n', padding=False)
                solution['pixel_convention'] = 'zero-based preview column x, row y'
            else:
                solution['wcs_warning'] = 'No full WCS was produced; labels are unavailable.'
            return solution
