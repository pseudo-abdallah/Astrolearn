"""Geometry, uncertainty, resource integrity and offline identification checks."""

import hashlib
from io import BytesIO
import json
from pathlib import Path
import socket
import time
import urllib.request

from astropy.io import fits
from astropy.wcs import WCS
from fastapi.testclient import TestClient
import numpy as np
from PIL import Image
import pytest

from astrolearn.identification import OfflineIdentifier, image_wcs, match_unique, project_records
from astrolearn.main import create_app
from astrolearn.solver import AstapSolver

ROOT = Path(__file__).resolve().parent.parent


def test_failed_thumbnail_solve_has_actionable_input_checks(tmp_path):
    class NoMatchSolver:
        def status(self):
            return {'available': True, 'databases': [{'name': 'D05', 'min_fov_deg': 0.6, 'max_fov_deg': 6}]}

        def solve(self, image, options):
            raise ValueError('No solution. Check the field of view and star database.')

    buffer = BytesIO()
    Image.new('RGB', (512, 511)).save(buffer, format='PNG')
    with TestClient(create_app(tmp_path / 'help.sqlite', solver=NoMatchSolver())) as client:
        image = client.post('/api/v1/images', content=buffer.getvalue()).json()
        job = client.post(f"/api/v1/images/{image['id']}/solve", json={}).json()
        for _ in range(100):
            job = client.get('/api/v1/solves/' + job['id']).json()
            if job['status'] == 'failed':
                break
            time.sleep(0.01)
        assert job['status'] == 'failed'
        notes = ' '.join(job['diagnostics'])
        assert '512 × 511' in notes
        assert '0.6' in notes and 'D05' in notes
        assert 'pixels are not degrees' in notes
        assert 'extracts its own usable stars' in notes
        assert job['solution'] is None


def wcs_solution():
    mapping = WCS(naxis=2)
    mapping.wcs.ctype = ['RA---TAN', 'DEC--TAN']
    mapping.wcs.crval = [359.99, 30]
    mapping.wcs.crpix = [50, 50]
    angle = np.deg2rad(33)
    mapping.wcs.cd = np.array([[-np.cos(angle), np.sin(angle)], [np.sin(angle), np.cos(angle)]]) * 0.001
    header = mapping.to_header()
    header['NAXIS'], header['NAXIS1'], header['NAXIS2'] = 2, 100, 100
    return {'wcs_header': header.tostring(sep='\n', padding=False)}


def make_identifier(tmp_path, mapping):
    def record(key, x, y, kind='star'):
        point = mapping.pixel_to_world(x, y)
        return {'id': key, 'name': key, 'proper_name': True, 'kind': kind,
                'ra_deg': float(point.ra.deg), 'dec_deg': float(point.dec.deg), 'magnitude': 3.0}
    content = {'stars': [record('Matched star', 20, 70), record('Expected star', 65, 30),
                         record('Outside', 120, 10)], 'objects': [record('M-test', 50, 50, 'deep-sky object')]}
    raw = json.dumps(content).encode()
    (tmp_path / 'catalog.json').write_bytes(raw)
    (tmp_path / 'manifest.json').write_text(json.dumps({'catalog_sha256': hashlib.sha256(raw).hexdigest(),
        'star_count': 3, 'named_star_count': 3, 'object_count': 1, 'source': 'test-only geometry fixture',
        'revision': 'fixture', 'license': 'test', 'reference_frame': 'ICRS/J2000'}))
    return OfflineIdentifier(tmp_path)


def test_rotated_wcs_ra_wrap_and_preview_row_alignment():
    mapping = image_wcs(wcs_solution())
    point = mapping.pixel_to_world(20, 70)
    records, xy = project_records(mapping, [{'ra_deg': point.ra.deg, 'dec_deg': point.dec.deg}], 100, 100)
    assert len(records) == 1
    assert xy[0] == pytest.approx([20, 70], abs=1e-7)
    assert xy[0][1] != pytest.approx(99 - 70), 'Preview y must not be silently flipped'


def test_large_clipped_core_uncertainty_does_not_relax_normal_or_blended_matches(tmp_path):
    solution = wcs_solution()
    identifier = make_identifier(tmp_path,image_wcs(solution))
    source = {'x':24.5,'y':70,'area':12000,'profile':'saturated candidate'}
    analysis = {'width':1000,'height':1000,'sources':[source]}
    result = identifier.identify(solution,analysis)
    assert result['matched_stars'][0]['name'] == 'Matched star'
    assert result['matched_stars'][0]['residual_px'] == pytest.approx(4.5)
    assert result['matched_stars'][0]['match_radius_px'] == 6
    analysis['sources'] = [{**source,'area':20,'profile':'compact candidate'}]
    assert identifier.identify(solution,analysis)['matched_stars'] == []
    analysis['sources'] = [source,{**source,'x':22}]
    assert identifier.identify(solution,analysis)['matched_stars'] == []


def test_unique_matching_rejects_blends_and_duplicate_sources():
    matches, ambiguous = match_unique(np.array([[10., 10.], [11., 10.], [70., 70.]]), np.array([[10., 10.], [70., 70.]]), 3)
    assert [(a, b) for a, b, _ in matches] == [(2, 1)]
    assert ambiguous == 1
    matches, _ = match_unique(np.array([[10., 10.]]), np.array([[9., 10.], [11., 10.]]), 3)
    assert matches == []


def test_antennae_components_named_from_solved_footprint():
    mapping = WCS(naxis=2)
    mapping.wcs.ctype = ['RA---TAN', 'DEC--TAN']
    mapping.wcs.crval = [180.471376, -18.881796]
    mapping.wcs.crpix = [528, 531]
    mapping.wcs.cdelt = [-.2/3600, .2/3600]
    solution = {'wcs_header': mapping.to_header().tostring(sep='\n', padding=False)}
    result = OfflineIdentifier().identify(solution, {'width':1055,'height':1061,'sources':[]})
    objects = {obj['id']:obj for obj in result['expected_objects']}
    for key in ('NGC4038', 'NGC4039'):
        assert 'Antennae Galaxies' in objects[key]['name']
        assert objects[key]['evidence'] == 'expected'
    assert result['matched_star_count'] == 0


def test_expected_objects_are_not_detections(tmp_path):
    solution = wcs_solution()
    identifier = make_identifier(tmp_path, image_wcs(solution))
    result = identifier.identify(solution, {'width': 100, 'height': 100, 'sources': [{'x': 20.2, 'y': 70.1}, {'x': 90, 'y': 90}]})
    assert result['matched_star_count'] == 1
    assert result['matched_stars'][0]['name'] == 'Matched star'
    assert result['matched_stars'][0]['residual_px'] < 0.3
    assert result['unidentified_source_count'] == 1
    assert [r['name'] for r in result['expected_stars']] == ['Expected star']
    assert result['expected_objects'][0]['evidence'] == 'expected'
    assert result['expected_objects'][0]['id'] == 'M-test'
    empty = identifier.identify(solution, {'width': 100, 'height': 100, 'sources': []})
    assert empty['matched_star_count'] == 0
    assert len(empty['expected_stars']) == 2
    assert not any(x['name'] == 'Outside' for x in empty['expected_stars'])


def test_mapping_and_catalog_are_required(tmp_path):
    with pytest.raises(ValueError, match='Solve the image again'):
        image_wcs({})
    assert OfflineIdentifier(tmp_path / 'missing').status()['available'] is False
    (tmp_path / 'catalog.json').write_text('{}')
    (tmp_path / 'manifest.json').write_text(json.dumps({'catalog_sha256': 'wrong'}))
    assert OfflineIdentifier(tmp_path).status()['available'] is False


def test_bundled_names_and_resource_provenance():
    identifier = OfflineIdentifier()
    status = identifier.status()
    assert status['available'] and status['offline']
    assert status['star_count'] > 40000
    assert status['object_count'] == 110


@pytest.mark.skipif(not AstapSolver().status()['available'], reason='Real offline ASTAP not installed')
@pytest.mark.parametrize('format', ['PNG', 'FITS'])
def test_real_identification_without_python_network(tmp_path, monkeypatch, format):
    def blocked(*args, **kwargs):
        raise AssertionError('External network access attempted during offline workflow')
    monkeypatch.setattr(socket, 'create_connection', blocked)
    monkeypatch.setattr(urllib.request, 'urlopen', blocked)
    data = (ROOT / 'samples/synthetic-orion-wide.png').read_bytes()
    if format == 'FITS':
        # A mirrored FITS array tests a different parity from the raster fixture.
        array = np.asarray(Image.open(BytesIO(data)).convert('L'))[:, ::-1]
        buffer = BytesIO()
        fits.PrimaryHDU(array).writeto(buffer)
        data = buffer.getvalue()
    database = tmp_path / 'offline.sqlite'
    with TestClient(create_app(database)) as client:
        image = client.post('/api/v1/images', content=data).json()
        job = client.post(f"/api/v1/images/{image['id']}/solve", json={'fov_deg': 40}).json()
        for _ in range(300):
            job = client.get('/api/v1/solves/' + job['id']).json()
            if job['status'] not in {'queued', 'running'}:
                break
            time.sleep(0.1)
        assert job['status'] == 'solved', job
        result = job['identification']
        assert result['status'] == 'ready', result
        assert result['matched_star_count'] > 500
        by_name = {item['name']: item for item in result['matched_stars']}
        assert {'Betelgeuse', 'Bellatrix'} <= by_name.keys()
        # A different parity can produce a slightly different ASTAP fit at the
        # edge. Do not widen the matching radius just to force a name there.
        if format == 'PNG':
            assert 'Rigel' in by_name
        else:
            assert 'Rigel' in by_name or any(r['name'] == 'Rigel' and r['evidence'] == 'expected' for r in result['expected_stars'])
        betelgeuse = by_name['Betelgeuse']
        assert betelgeuse['id'] == 'HIP 27989'
        assert betelgeuse['evidence'] == 'matched' and betelgeuse['residual_px'] <= 3
        assert any(r['id'] == 'M42' and r['evidence'] == 'expected' for r in result['expected_objects'])
        assert client.get(f"/api/v1/solves/{job['id']}/wcs").status_code == 200
        assert client.get(f"/api/v1/images/{image['id']}/latest-solve").json()['id'] == job['id']
        saved = client.post('/api/v1/sessions', json={'image_id': image['id'], 'solve_id': job['id'], 'site': {
            'target_id': 'vega', 'latitude': 29.3, 'longitude': 48, 'utc': '2026-11-02T18:00:00Z'}}).json()
        # Names must come from the image WCS, never from the chosen target (Vega).
        assert saved['target'] == 'Vega'
        assert saved['identification']['matched_stars'] == result['matched_stars']
        assert 'Vega' not in by_name
    with TestClient(create_app(database)) as restarted:
        row = restarted.get('/api/v1/sessions').json()[0]
        assert row['identification']['named_match_count'] > 10
        restored = restarted.get('/api/v1/solves/' + row['solve_id']).json()
        assert restored['solution']['wcs_header'] == job['solution']['wcs_header']
