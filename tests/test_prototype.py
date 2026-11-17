"""Image, astronomy, persistence, simulated motion and real offline-solver tests."""

from io import BytesIO
from pathlib import Path
import time

import numpy as np
from PIL import Image
import pytest
from fastapi.testclient import TestClient

from astrolearn.main import create_app
from astrolearn.imaging import decode_image, detect_sources
from astrolearn.solver import AstapSolver, SolveOptions, parse_solution

ROOT = Path(__file__).resolve().parent.parent
SITE = {'target_id': 'betelgeuse', 'latitude': 29.3759, 'longitude': 47.9774,
        'elevation_m': 0, 'utc': '2026-11-02T18:00:00Z'}


def picture():
    buffer = BytesIO()
    Image.new('RGB', (100, 80), (10, 10, 10)).save(buffer, format='PNG')
    return buffer.getvalue()


class MissingSolver:
    def status(self):
        return {'available': False, 'offline': True}


def test_image_upload_validation_and_no_cloud(tmp_path):
    with TestClient(create_app(tmp_path / 'test.sqlite', solver=MissingSolver())) as client:
        assert client.post('/api/v1/images', content=b'not an image').status_code == 422
        response = client.post('/api/v1/images', content=picture())
        assert response.status_code == 201
        image = response.json()
        assert image['analysis']['count'] == 0
        assert client.get(image['preview_url']).headers['content-type'] == 'image/png'
        assert client.get(image['original_url']).status_code == 200
        assert client.get('/api/v1/images').json()[0]['id'] == image['id']
        assert client.post(f"/api/v1/images/{image['id']}/solve", json={}).status_code == 503
        assert client.get('/api/v1/images/missing').status_code == 404
        assert client.get('/api/v1/solves/missing').status_code == 404
        assert client.get('/static/app.js').status_code == 200
        assert client.get('/api/v1/prototype/status').json()['camera'] == 'not configured'


def test_source_detection_and_fits():
    array = np.zeros((100, 100, 3), dtype='uint8')
    array[20:23, 30:33] = 255
    array[70:73, 60:63] = 200
    assert detect_sources(array)['count'] == 2
    from astropy.io import fits
    data = BytesIO()
    fits.PrimaryHDU(array[:, :, 0].astype('uint16')).writeto(data)
    rgb, png, extension = decode_image(data.getvalue())
    assert rgb.shape == array.shape and extension == '.fits'
    assert png.startswith(b'\x89PNG')


def test_astronomy_offline_and_validation(tmp_path):
    with TestClient(create_app(tmp_path / 'test.sqlite')) as client:
        assert len(client.get('/api/v1/catalog').json()) >= 20
        result = client.post('/api/v1/astronomy/position', json=SITE)
        assert result.status_code == 200
        position = result.json()
        assert 0 <= position['azimuth_deg'] < 360
        assert -90 <= position['altitude_deg'] <= 90
        assert position['ra_deg'] == pytest.approx(88.7929)
        assert position['coordinate_frame'] == 'ICRS/J2000'
        for changes in ({'latitude': 91}, {'target_id': 'unknown'}, {'utc': '2026-11-02T18:00:00'}):
            assert client.post('/api/v1/astronomy/position', json={**SITE, **changes}).status_code == 422
        # The local ephemeris path is optional but tested when installed.
        if (ROOT / 'resources/de421.bsp').is_file():
            result = client.post('/api/v1/astronomy/position', json={**SITE, 'target_id': 'jupiter'})
            assert result.status_code == 200
            assert 'Skyfield' in result.json()['engine']


def test_simulation_stop_latches_and_requires_reset(tmp_path):
    with TestClient(create_app(tmp_path / 'test.sqlite')) as client:
        command = {'axis': 'ra', 'steps': 200}
        moved = client.post('/api/v1/mount/move', json=command).json()
        assert moved['state'] == 'moving' and moved['physical_hardware'] is False
        assert client.post('/api/v1/mount/move', json=command).status_code == 409
        assert client.post('/api/v1/mount/stop').json()['state'] == 'stopped'
        assert client.post('/api/v1/mount/move', json=command).status_code == 409
        assert client.post('/api/v1/mount/reset').json()['state'] == 'idle'
        assert client.post('/api/v1/mount/move', json={'axis': 'bad', 'steps': 4}).status_code == 422
        assert client.post('/api/v1/mount/move', json={'axis': 'ra', 'steps': 4.5}).status_code == 422


def test_unsolved_session_persists_without_invented_pointing(tmp_path):
    path = tmp_path / 'test.sqlite'
    with TestClient(create_app(path)) as client:
        image = client.post('/api/v1/images', content=picture()).json()
        saved = client.post('/api/v1/sessions', json={'image_id': image['id'], 'site': SITE, 'notes': '<script>hello</script>'})
        assert saved.status_code == 201
        row = saved.json()
        assert row['pointing_error_deg'] is None
        assert row['field_center_within_threshold'] is False
        assert row['tracking_duration_s'] == 0
    with TestClient(create_app(path)) as restarted:
        assert restarted.get('/api/v1/sessions').json() == [row]
        assert restarted.get('/api/v1/sessions/export').json() == [row]
        assert restarted.get(image['preview_url']).status_code == 200


@pytest.mark.parametrize('text', [
    'PLTSOLVD=F', 'PLTSOLVD=T\nCRVAL1=nan\nCRVAL2=0\nCDELT2=1',
    'PLTSOLVD=T\nCRVAL1=360\nCRVAL2=0\nCDELT2=1',
])
def test_invalid_solver_output_never_becomes_success(text):
    with pytest.raises(ValueError):
        parse_solution(text)


def test_valid_solver_output_units():
    result = parse_solution('PLTSOLVD=T\nCRVAL1=120\nCRVAL2=-30\nCDELT2=0.001\nCROTA2=15')
    assert result['pixel_scale_arcsec'] == pytest.approx(3.6)
    assert result['ra_deg'] == 120
    with pytest.raises(ValueError):
        SolveOptions(ra_deg=12)
    with pytest.raises(ValueError):
        SolveOptions(radius_deg=5)


class FailedSolver:
    """Test-only failure provider; production always calls the real ASTAP binary."""
    def status(self):
        return {'available': True, 'offline': True}

    def solve(self, image, options):
        raise ValueError('Not enough stars detected to solve this image.')


def wait_job(client, job_id):
    for _ in range(200):
        result = client.get('/api/v1/solves/' + job_id).json()
        if result['status'] not in {'queued', 'running'}:
            return result
        time.sleep(0.1)
    pytest.fail('Background solve did not finish')


def test_background_failure_and_retry(tmp_path):
    with TestClient(create_app(tmp_path / 'test.sqlite', solver=FailedSolver())) as client:
        image = client.post('/api/v1/images', content=picture()).json()
        for _ in range(2):
            response = client.post(f"/api/v1/images/{image['id']}/solve", json={})
            assert response.status_code == 202
            job = wait_job(client, response.json()['id'])
            assert job['status'] == 'failed' and job['solution'] is None
            assert client.get('/api/v1/health').status_code == 200


@pytest.mark.skipif(not AstapSolver().status()['available'] or not (ROOT / 'samples/synthetic-orion-wide.png').exists(), reason='Install ASTAP/W08 and generate the integration fixture first')
def test_real_offline_plate_solve_to_saved_comparison(tmp_path):
    with TestClient(create_app(tmp_path / 'real.sqlite')) as client:
        image = client.post('/api/v1/images', content=(ROOT / 'samples/synthetic-orion-wide.png').read_bytes()).json()
        response = client.post(f"/api/v1/images/{image['id']}/solve", json={'fov_deg': 40})
        assert response.status_code == 202
        job = wait_job(client, response.json()['id'])
        assert job['status'] == 'solved', job
        saved = client.post('/api/v1/sessions', json={'image_id': image['id'], 'solve_id': job['id'], 'site': SITE}).json()
        assert saved['pointing_error_deg'] < 0.1
        assert saved['field_center_within_threshold'] is True
        other = client.post('/api/v1/images', content=picture()).json()
        assert client.post('/api/v1/sessions', json={'image_id': other['id'], 'solve_id': job['id'], 'site': SITE}).status_code == 422
