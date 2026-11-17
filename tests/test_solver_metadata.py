"""Calibration is a search aid, not proof that the pixels match the sky."""

import numpy as np
import pytest
from astropy.io import fits
from astropy.wcs import WCS
from fastapi.testclient import TestClient

from astrolearn.main import create_app
from astrolearn.solver import SolveOptions, SolverFailure, effective_solve_options, fits_calibration
from tests.test_prototype import picture, wait_job


def test_fits_hints_and_user_override(tmp_path):
    mapping = WCS(naxis=2)
    mapping.wcs.crpix = [60.5, 50.5]
    mapping.wcs.crval = [297.6958, 8.8683]
    mapping.wcs.cdelt = [-0.01, 0.01]
    mapping.wcs.ctype = ['RA---TAN', 'DEC--TAN']
    path = tmp_path / 'field.fits'
    fits.writeto(path, np.zeros((100, 120)), mapping.to_header())
    hints = fits_calibration(path)
    assert hints['ra_deg'] == pytest.approx(297.6958)
    assert hints['fov_deg'] == pytest.approx(1, abs=0.001)
    derived = effective_solve_options(SolveOptions(), hints)
    assert derived.ra_deg == hints['ra_deg']
    explicit = SolveOptions(fov_deg=2, ra_deg=10, dec_deg=-20, radius_deg=5)
    assert effective_solve_options(explicit, hints) == explicit
    # A FITS upload exposes hints without silently marking it solved.
    with TestClient(create_app(tmp_path / 'metadata.sqlite')) as client:
        image = client.post('/api/v1/images', content=path.read_bytes()).json()
        assert image['calibration']['fov_deg'] == hints['fov_deg']
        assert client.get(f"/api/v1/images/{image['id']}/latest-solve").json() is None


def test_missing_or_invalid_wcs_is_not_a_calibration(tmp_path):
    path = tmp_path / 'uncalibrated.fits'
    fits.writeto(path, np.zeros((50, 50)))
    assert fits_calibration(path) is None
    assert fits_calibration(tmp_path / 'missing.fits') is None
    assert fits_calibration(tmp_path / 'thumbnail.png') is None


class LoggedFailure:
    def status(self):
        return {'available': True, 'offline': True}

    def solve(self, image, options):
        raise SolverFailure('No matching star pattern.', '34 stars; no solution found.')


def test_native_failure_log_persists_without_success(tmp_path):
    database = tmp_path / 'failure.sqlite'
    with TestClient(create_app(database, solver=LoggedFailure())) as client:
        image = client.post('/api/v1/images', content=picture()).json()
        job = client.post(f"/api/v1/images/{image['id']}/solve", json={}).json()
        result = wait_job(client, job['id'])
        assert result['status'] == 'failed' and result['solution'] is None
        assert '34 stars' in client.get(f"/api/v1/solves/{job['id']}/log").text
    with TestClient(create_app(database, solver=LoggedFailure())) as client:
        assert client.get(f"/api/v1/solves/{job['id']}/log").status_code == 200
def test_astap_timeout_retains_native_log_before_cleanup(tmp_path, monkeypatch):
    import subprocess
    from pathlib import Path
    from PIL import Image
    import pytest
    from astrolearn.solver import AstapSolver, SolveOptions, SolverFailure
    image = tmp_path/'image.png'
    Image.new('L',(100,100)).save(image)
    solver = AstapSolver()
    monkeypatch.setattr(solver,'status',lambda: {'available':True})
    recorded = {}
    def timeout(command, **kwargs):
        base = Path(command[command.index('-o')+1])
        recorded['folder'] = base.parent
        base.with_suffix('.log').write_text('Using star database D50\n503 stars, 424 quads selected in the image.')
        raise subprocess.TimeoutExpired(command,kwargs['timeout'])
    monkeypatch.setattr(subprocess,'run',timeout)
    with pytest.raises(SolverFailure,match='timed out after 7 seconds') as error:
        solver.solve(image,SolveOptions(),timeout_seconds=7)
    assert 'D50' in error.value.log and '503 stars' in error.value.log
    assert not recorded['folder'].exists()


