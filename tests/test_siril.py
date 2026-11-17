"""Exercise real local Gaia solving and mapping parity, not a canned WCS result."""

import json
from pathlib import Path
import socket
import urllib.request

import numpy as np
from astropy.io import fits
from astropy.wcs import WCS
import cv2
import pytest
from fastapi.testclient import TestClient

from astrolearn.imaging import detect_sources
from astrolearn.main import create_app
from astrolearn.siril_solver import SirilSolver
from tests.test_prototype import wait_job

ROOT = Path(__file__).resolve().parent.parent


def test_nonzero_crop_offset_preserves_rotated_sip_coordinates():
    from astropy.wcs import Sip
    from astrolearn.siril_solver import crop_mapping
    original = WCS(naxis=2)
    original.wcs.ctype = ['RA---TAN-SIP','DEC--TAN-SIP']
    original.wcs.crval = [83,-5]
    original.wcs.crpix = [300,200]
    original.wcs.cd = np.array([[-.0004,.0002],[.0002,.0004]])
    a,b = np.zeros((3,3)),np.zeros((3,3))
    a[2,0],b[0,2] = 1e-5,-1e-5
    original.sip = Sip(a,b,None,None,original.wcs.crpix)
    header,_ = crop_mapping(original.to_header(relax=True).tostring(sep='\n',padding=False),500,700,1600,1200)
    full = WCS(fits.Header.fromstring(header,sep='\n'))
    x,y = np.array([20,300,550]),np.array([20,200,350])
    assert np.max(original.pixel_to_world(x,y).separation(full.pixel_to_world(x+500,y+700)).arcsec)<1e-6


def test_clipped_star_center_is_measured_from_pixels():
    rgb = np.zeros((160, 160, 3), dtype=np.uint8)
    cv2.line(rgb, (80, 20), (80, 120), (150, 150, 150), 1)
    # Diffraction adds light; it must not paint a dark cut through the core.
    cv2.circle(rgb, (80, 70), 16, (255, 255, 255), -1)
    result = detect_sources(rgb)
    cores = [s for s in result['sources'] if s.get('profile') == 'saturated candidate']
    assert len(cores) == 1
    assert [cores[0]['x'], cores[0]['y']] == pytest.approx([80, 70], abs=0.5)
    assert result['analysis_version'] == 3


@pytest.mark.skipif(not SirilSolver().status()['available'], reason='Install verified Siril/Gaia resources first')
@pytest.mark.parametrize('mirrored', [False, True])
def test_real_siril_offline_wcs_matches_survey_pixels(tmp_path, monkeypatch, mirrored):
    def blocked(*args, **kwargs):
        raise AssertionError('Unexpected Python internet access')
    monkeypatch.setattr(socket, 'create_connection', blocked)
    monkeypatch.setattr(urllib.request, 'urlopen', blocked)
    path = ROOT / 'samples/altair-dss2-red-1deg.fits'
    array, header = fits.getdata(path, header=True)
    original = WCS(header).celestial
    if mirrored:
        array = array[:, ::-1]
    # Strip all WCS: the solver cannot reuse the known reference calibration.
    from io import BytesIO
    buffer = BytesIO()
    fits.PrimaryHDU(array).writeto(buffer)
    with TestClient(create_app(tmp_path / 'siril.sqlite')) as client:
        image = client.post('/api/v1/images', content=buffer.getvalue()).json()
        assert image['calibration'] is None
        job = client.post(f"/api/v1/images/{image['id']}/solve", json={
            'backend': 'siril', 'fov_deg': 1, 'ra_deg': 297.6958, 'dec_deg': 8.8683, 'radius_deg': 1}).json()
        result = wait_job(client, job['id'])
        assert result['status'] == 'solved', result
        assert result['solution']['solver'] == 'Siril / local Gaia DR3'
        solved = WCS(fits.Header.fromstring(result['solution']['wcs_header'], sep='\n')).celestial
        x = np.array([100, 100, 600, 1100, 1100])
        y = np.array([100, 1100, 600, 100, 1100])
        expected = original.pixel_to_world(1199 - x if mirrored else x, y)
        assert np.max(expected.separation(solved.pixel_to_world(x, y)).arcsec) < 5
        assert client.get(f"/api/v1/solves/{job['id']}/wcs").status_code == 200
