import time

from fastapi.testclient import TestClient
import pytest

from astrolearn.main import create_app
from astrolearn.mount import SimulatedMount
from astrolearn.siril_solver import SirilSolver
from astrolearn.solver import ROOT

SITE = {'target_id': 'vega', 'latitude': 29.3759, 'longitude': 47.9774, 'utc': '2026-11-03T00:00:00Z'}


def finished(client, id):
    for _ in range(400):
        result = client.get('/api/v1/analyses/' + id).json()
        if result['status'] not in {'queued', 'running'}:
            return result
        time.sleep(.1)
    pytest.fail('Automatic analysis did not finish')


class NeverPlateSolve:
    def status(self):
        return {'available': True, 'offline': True}

    def solve(self, image, options):
        raise AssertionError('A resolved Moon image should take the close-up path')


@pytest.mark.skipif(not (ROOT/'resources/solar-model/manifest.json').exists(), reason='Install model first')
def test_automatic_closeup_does_not_fabricate_coordinates(tmp_path):
    database = tmp_path / 'automatic.sqlite'
    with TestClient(create_app(database, solver=NeverPlateSolve())) as client:
        image = client.post('/api/v1/images', content=(ROOT/'samples/solar/moon.png').read_bytes()).json()
        response = client.post(f"/api/v1/images/{image['id']}/analyze", json={})
        assert response.status_code == 202
        result = finished(client, response.json()['id'])
        assert result['status'] == 'completed' and result['kind_result'] == 'closeup', result
        assert result['solar']['objects'][0]['name'] == 'Possible Moon'
        assert 'plate' not in result and 'ra_deg' not in result['solar']['objects'][0]
        assert client.get(f"/api/v1/images/{image['id']}/latest-solve").json() is None
    with TestClient(create_app(database, solver=NeverPlateSolve())) as client:
        assert client.get(f"/api/v1/images/{image['id']}/latest-analysis").json()['id'] == result['id']


@pytest.mark.skipif(not SirilSolver().status()['available'], reason='Install Siril/Gaia first')
def test_automatic_field_with_real_solver_and_cached_result(tmp_path):
    with TestClient(create_app(tmp_path / 'field.sqlite')) as client:
        image = client.post('/api/v1/images', content=(ROOT/'samples/altair-dss2-red-1deg.fits').read_bytes()).json()
        url = f"/api/v1/images/{image['id']}/analyze"
        for _ in range(2):
            job = client.post(url, json={'options': {'backend': 'siril'}, 'observation': SITE, 'reuse_solution': True}).json()
            result = finished(client, job['id'])
            assert result['status'] == 'completed' and result['kind_result'] == 'field', result
            assert result['plate']['status'] == 'solved'
            assert result['plate']['solution']['ra_deg'] == pytest.approx(297.6958, abs=.01)
            assert result['solar']['mode'] == 'field'
        assert result['solve_id'] == result['plate']['id']
        # Re-uploading the exact pixels must retain an earlier verified WCS,
        # including when an intervening retry failed.
        from astrolearn.prototype_store import PrototypeStore
        store = PrototypeStore(tmp_path / 'field.sqlite')
        store.new('solve', image_id=image['id'], status='failed', message='Failed retry')
        copy = client.post('/api/v1/images', content=(ROOT/'samples/altair-dss2-red-1deg.fits').read_bytes()).json()
        job = client.post(f"/api/v1/images/{copy['id']}/analyze", json={'reuse_solution': True}).json()
        recovered = finished(client, job['id'])
        assert recovered['plate']['reused_from_solve_id'] == result['solve_id']
        assert recovered['plate']['image_id'] == copy['id']
        assert recovered['plate']['solution'] == result['plate']['solution']


def test_disk_routing_rejects_horizon_and_white_border():
    import cv2
    import numpy as np
    from astrolearn.solar import disk_box
    rng = np.random.default_rng(42)
    sky = np.zeros((400, 600, 3), dtype=np.uint8)
    for x, y in rng.integers([10, 10], [590, 280], size=(100, 2)):
        cv2.circle(sky, (int(x), int(y)), 1, (180, 180, 180), -1)
    bordered = sky.copy()
    cv2.rectangle(bordered, (0, 0), (599, 399), (255, 255, 255), 2)
    assert disk_box(bordered) is None
    sky[290:] = 100
    assert disk_box(sky) is None
    # Preserve isolated disks and elongated ringed planets.
    disk = np.zeros_like(sky)
    cv2.ellipse(disk, (300, 200), (90, 35), 0, 0, 360, (220, 220, 220), -1)
    assert disk_box(disk) is not None


def test_solution_cache_does_not_match_different_pixels(tmp_path):
    from astrolearn.prototype_store import PrototypeStore
    store = PrototypeStore(tmp_path / 'cache.sqlite')
    store.initialize()
    for key, data in [('first', b'original'), ('copy', b'original'), ('other', b'different')]:
        (store.files / (key+'.png')).write_bytes(data)
        store.save('image', {'id': key, 'original': key+'.png'})
    success = store.new('solve', image_id='first', status='solved', solution={'test_fixture': True})
    store.new('solve', image_id='first', status='failed')
    assert store.successful_solve('copy')['id'] == success['id']
    assert store.successful_solve('first')['id'] == success['id']
    assert store.successful_solve('other') is None


def test_default_analysis_invokes_solver_even_with_saved_success(tmp_path):
    from astrolearn.prototype_store import PrototypeStore
    class CountingFailure:
        calls = 0
        def status(self): return {'available': True}
        def solve(self, image, options):
            self.calls += 1
            raise ValueError('Fresh native solve attempted')
    solver = CountingFailure()
    database = tmp_path/'fresh.sqlite'
    with TestClient(create_app(database, solver=solver)) as client:
        image = client.post('/api/v1/images', content=(ROOT/'samples/synthetic-orion-wide.png').read_bytes()).json()
        store = PrototypeStore(database)
        store.new('solve', image_id=image['id'], status='solved', solution={'test_only': True})
        response = client.post(f"/api/v1/images/{image['id']}/analyze", json={})
        result = finished(client, response.json()['id'])
        assert solver.calls == 1
        assert result['plate']['status'] == 'failed'
        assert 'Fresh native solve attempted' in result['message']
        sources = client.get(f"/api/v1/images/{image['id']}/sources").json()
        assert sources['count'] == len(sources['sources']) > 100


def test_dense_sources_retain_bright_bottom_half_core():
    import cv2
    import numpy as np
    from astrolearn.imaging import detect_sources
    sky = np.zeros((1200,1200,3), dtype=np.uint8)
    for y in range(8, 490, 8):
        for x in range(8, 690, 8):
            cv2.rectangle(sky,(x,y),(x+1,y+1),(80,80,80),-1)
    cv2.circle(sky,(350,1000),65,(255,255,255),-1)
    result = detect_sources(sky)
    assert result['truncated'] and result['count'] == 2000
    assert any(s.get('profile')=='saturated candidate' and abs(s['x']-350)<1 and
               abs(s['y']-1000)<1 for s in result['sources'])


def test_target_selection_drives_simulated_coordinates_and_stop(tmp_path):
    with TestClient(create_app(tmp_path / 'mount.sqlite')) as client:
        body = {**SITE, 'client_id': 'test-browser', 'sequence': 2}
        response = client.post('/api/v1/mount/goto', json=body)
        assert response.status_code == 200
        value = response.json()
        assert value['mount']['state'] == 'moving'
        assert value['mount']['target']['id'] == 'vega'
        assert value['mount']['target']['destination']['ra_deg'] == value['position']['ra_deg']
        assert value['mount']['physical_hardware'] is False
        assert client.post('/api/v1/mount/goto', json={**body, 'sequence': 1, 'target_id': 'moon'}).status_code == 409
        assert client.get('/api/v1/mount').json()['target']['id'] == 'vega'
        client.post('/api/v1/mount/stop')
        assert client.post('/api/v1/mount/goto', json={**body, 'sequence': 3}).status_code == 409
        client.post('/api/v1/mount/reset')
        assert client.post('/api/v1/mount/goto', json={**body, 'sequence': 4}).status_code == 200


def test_simulator_reaches_coordinates_without_step_calibration():
    mount = SimulatedMount()
    position = {'target': {'id': 'test', 'name': 'Test'}, 'utc': SITE['utc'],
                'ra_deg': 359, 'dec_deg': -20, 'altitude_deg': -5, 'azimuth_deg': 359}
    mount.goto(position, 'browser', 1)
    start, goal, _ = mount.slew
    mount.slew = (start, goal, time.monotonic()-4)
    result = mount.status()
    assert result['state'] == 'idle' and result['pointing']['azimuth_deg'] == pytest.approx(359)
    assert result['pointing']['altitude_deg'] == -5
    assert result['positions_steps'] == {'ra': 0, 'dec': 0}
