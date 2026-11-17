from pathlib import Path
import socket
import urllib.request

from astropy.io import fits
from astropy.wcs import WCS
import numpy as np
import pytest
from fastapi.testclient import TestClient

from astrolearn.main import create_app
from astrolearn.solar import solar_positions, identify_field, classify_closeup, disk_box, ROOT
from astrolearn.astronomy import SiteRequest
from astrolearn.prototype_store import PrototypeStore
from tests.test_prototype import picture

SITE = {'target_id': 'vega', 'latitude': 29.3759, 'longitude': 47.9774, 'utc': '2026-11-03T00:00:00Z'}
HAS_PACKS = (ROOT / 'resources/ephemerides/jup365-2025-2028.bsp').is_file()


def test_blank_closeup_does_not_receive_name():
    result = classify_closeup(np.zeros((200, 200, 3), dtype=np.uint8))
    assert result['status'] == 'unknown' and not result['objects']
    assert disk_box(np.ones((200, 200, 3), dtype=np.uint8)*255) is None


@pytest.mark.parametrize('target', ['uranus', 'neptune'])
def test_outer_planets_available_in_target_selector(tmp_path, target):
    with TestClient(create_app(tmp_path / 'outer.sqlite')) as client:
        assert target in {t['id'] for t in client.get('/api/v1/catalog').json()}
        result = client.post('/api/v1/astronomy/position', json={**SITE, 'target_id': target})
        assert result.status_code == 200, result.text
        assert 0 <= result.json()['ra_deg'] < 360


def test_solar_routes_validation_and_telemetry(tmp_path):
    with TestClient(create_app(tmp_path / 'solar.sqlite')) as client:
        image = client.post('/api/v1/images', content=picture()).json()
        url = f"/api/v1/images/{image['id']}/solar-analysis"
        assert client.get(url).json() is None
        closeup = client.post(url, json={'mode': 'closeup'}).json()
        assert closeup['status'] == 'unknown'
        assert client.get(url).json()['id'] == closeup['id']
        assert client.post(url, json={'mode': 'field'}).status_code == 422
        store = PrototypeStore(tmp_path / 'solar.sqlite')
        store.save('solve', {'id': 'other', 'image_id': 'different-image', 'status': 'solved'})
        assert client.post(url, json={'mode': 'field', 'solve_id': 'other', 'observation': SITE}).status_code == 409
        with client.websocket_connect('/api/v1/telemetry') as ws:
            event = ws.receive_json()
            assert event['schema'] == 1 and event['sequence'] == 1
            assert event['camera'] == 'not configured' and 'prototype' in event['mode']
    with TestClient(create_app(tmp_path / 'solar.sqlite')) as client:
        assert client.get(url).json()['id'] == closeup['id']


@pytest.mark.skipif(not HAS_PACKS, reason='Install satellite excerpts first')
def test_satellite_positions_and_coverage_without_network(monkeypatch):
    # Skyfield probes urllib's call signature at import with an empty URL; it
    # cannot contact a host. Block real URL access after this compatibility probe.
    import skyfield.api
    import skyfield.iokit
    def blocked(*args, **kwargs):
        raise AssertionError('Internet access attempted')
    monkeypatch.setattr(socket, 'create_connection', blocked)
    monkeypatch.setattr(urllib.request, 'urlopen', blocked)
    monkeypatch.setattr(skyfield.iokit, 'urlopen', blocked)
    records, warnings = solar_positions(SiteRequest(**SITE), include_status=True)
    assert len(records) == 13 and not warnings
    assert {'Io', 'Europa', 'Ganymede', 'Callisto', 'Titan'} <= {r['name'] for r in records}
    assert all(0 <= r['ra_deg'] < 360 and -90 <= r['dec_deg'] <= 90 for r in records)
    old = SiteRequest(**{**SITE, 'utc': '2020-01-01T00:00:00Z'})
    records, warnings = solar_positions(old, include_status=True)
    assert len(records) == 8 and len(warnings) == 2
    assert 'Titan' not in {r['name'] for r in records}


@pytest.mark.skipif(not HAS_PACKS, reason='Install satellite excerpts first')
def test_moon_association_uses_position_not_selected_target():
    site = SiteRequest(**SITE)  # Selected target Vega cannot provide the name.
    records = solar_positions(site)
    jupiter = next(r for r in records if r['name'] == 'Jupiter')
    ganymede = next(r for r in records if r['name'] == 'Ganymede')
    mapping = WCS(naxis=2)
    mapping.wcs.crpix = [500.5, 500.5]
    mapping.wcs.crval = [jupiter['ra_deg'], jupiter['dec_deg']]
    mapping.wcs.cdelt = [-0.0005, 0.0005]
    mapping.wcs.ctype = ['RA---TAN', 'DEC--TAN']
    x, y = mapping.all_world2pix(ganymede['ra_deg'], ganymede['dec_deg'], 0)
    result = identify_field({'wcs_header': mapping.to_header().tostring(sep='\n', padding=False)},
                            {'width': 1000, 'height': 1000, 'sources': [{'x': float(x), 'y': float(y)}]}, site)
    moon = next(r for r in result['objects'] if r['name'] == 'Ganymede')
    assert moon['evidence'] == 'positional match' and moon['residual_px'] < .001
    assert next(r for r in result['objects'] if r['name'] == 'Jupiter')['evidence'] == 'expected'


@pytest.mark.skipif(not (ROOT / 'resources/solar-model/manifest.json').exists(), reason='Install local model first')
@pytest.mark.parametrize('filename,label', [('moon.png', 'Moon'), ('jupiter.jpg', 'Jupiter')])
def test_reference_visual_suggestion_is_not_a_solution(tmp_path, monkeypatch, filename, label):
    def blocked(*args, **kwargs):
        raise AssertionError('Internet access attempted')
    monkeypatch.setattr(socket, 'create_connection', blocked)
    monkeypatch.setattr(urllib.request, 'urlopen', blocked)
    with TestClient(create_app(tmp_path / 'visual.sqlite')) as client:
        image = client.post('/api/v1/images', content=(ROOT / 'samples/solar' / filename).read_bytes()).json()
        response = client.post(f"/api/v1/images/{image['id']}/solar-analysis", json={'mode': 'closeup'})
        assert response.status_code == 200, response.text
        result = response.json()
        assert result['status'] == 'suggestion'
        assert result['objects'][0]['name'] == 'Possible ' + label
        assert 'ra_deg' not in result['objects'][0]
        assert client.get(f"/api/v1/images/{image['id']}/latest-solve").json() is None
