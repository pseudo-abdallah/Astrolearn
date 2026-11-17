"""Offline predictions, measurements and cached remote facts have distinct evidence."""

import socket
import urllib.request

from fastapi.testclient import TestClient
import pytest

from astrolearn.main import create_app
from astrolearn.learning import parse_lightcurve
from astrolearn.prototype_store import PrototypeStore
from tests.test_prototype import SITE


@pytest.mark.parametrize('raw', [b'time,flux\n1,nan\n2,1\n3,1', b'time,flux\n1,-1\n2,-2\n3,-3', b'x,y\n1,2', b'time,flux\n1,2'])
def test_bad_measurements_rejected(raw):
    with pytest.raises(ValueError):
        parse_lightcurve(raw)


def test_local_map_and_lightcurves_without_network(tmp_path, monkeypatch):
    def blocked(*args, **kwargs):
        raise AssertionError('Unexpected internet request')
    monkeypatch.setattr(socket, 'create_connection', blocked)
    monkeypatch.setattr(urllib.request, 'urlopen', blocked)
    database = tmp_path / 'learning.sqlite'
    with TestClient(create_app(database)) as client:
        response = client.post('/api/v1/sky-map', json=SITE)
        assert response.status_code == 200
        stars = response.json()['stars']
        assert len(stars) > 100 and all(s['altitude_deg'] >= 0 for s in stars)
        polaris = next(s for s in stars if s['name'] == 'Polaris')
        assert polaris['altitude_deg'] == pytest.approx(SITE['latitude'], abs=1)
        data = client.post('/api/v1/lightcurves', content=b'time,flux\n2,10\n1,20\n3,10').json()
        assert data['points'] == [[1, 2], [2, 1], [3, 1]]
        assert client.post('/api/v1/lightcurves', content=b'wrong').status_code == 422
    with TestClient(create_app(database)) as client:
        assert client.get('/api/v1/lightcurves').json()[0] == data


def test_simbad_cache_does_not_upgrade_image_evidence(tmp_path, monkeypatch):
    database = tmp_path / 'cache.sqlite'
    with TestClient(create_app(database)) as client:
        # Explicit test fixture, not a production image identification result.
        store = PrototypeStore(database)
        store.save('solve', {'id': 'fixture', 'status': 'solved', 'identification': {
            'expected_stars': [{'id': 'HIP 27989', 'name': 'Betelgeuse', 'evidence': 'expected'}]}})
        url = '/api/v1/solves/fixture/object-details?object_id=HIP%2027989'
        monkeypatch.setattr('astrolearn.learning.fetch_simbad', lambda _: {'main_id': '* alf Ori', 'otype': 'Star'})
        assert client.get(url).json()['enrichment'] is None
        refreshed = client.post(url).json()
        assert refreshed['enrichment']['source'] == 'SIMBAD / CDS'
        assert refreshed['object']['evidence'] == 'expected'
        def unavailable(_):
            raise OSError('No connection')
        monkeypatch.setattr('astrolearn.learning.fetch_simbad', unavailable)
        failed = client.post(url).json()
        assert failed['enrichment'] == refreshed['enrichment'] and failed['online_error']
        assert client.get('/api/v1/solves/fixture/object-details?object_id=unknown').status_code == 404
    with TestClient(create_app(database)) as client:
        assert client.get(url).json()['enrichment'] == refreshed['enrichment']
