"""Two independent evidence paths: stellar WCS/ephemeris and visual suggestions.

Visual similarity never becomes a celestial coordinate solution or a confirmed
planet detection. Neither path takes the selected target as an answer.
"""

from functools import lru_cache
import hashlib
import json
from pathlib import Path
from threading import Lock
from typing import Literal
from contextlib import ExitStack

import cv2
import numpy as np
from PIL import Image
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict

from astrolearn.astronomy import ROOT, SiteRequest
from astrolearn.identification import image_wcs, project_records, match_unique
from astrolearn.imaging import decode_image

MODEL = ROOT / 'resources/solar-model'
BODIES = {'Moon': 'moon', 'Mercury': 'mercury', 'Venus': 'venus', 'Mars': 'mars',
          'Jupiter': 'jupiter barycenter', 'Saturn': 'saturn barycenter',
          'Uranus': 'uranus barycenter', 'Neptune': 'neptune barycenter'}
LABELS = list(BODIES) + ['Earth', 'not a solar-system close-up']
PROMPTS = [f'a telescope photograph of {name}' for name in LABELS[:-1]] + [
    'a photograph of a star field, galaxy, nebula, ordinary object, ball or empty sky']
SATELLITES = {'Io': (501, 'Jupiter'), 'Europa': (502, 'Jupiter'),
              'Ganymede': (503, 'Jupiter'), 'Callisto': (504, 'Jupiter'), 'Titan': (606, 'Saturn')}
PACKS = {'Jupiter': ('jup365-2025-2028.bsp', 5, 599), 'Saturn': ('sat441l-2025-2028.bsp', 6, 699)}


def resource_status():
    packs = []
    for name, (filename, _, _) in PACKS.items():
        path = ROOT / 'resources/ephemerides' / filename
        try:
            metadata = json.loads(path.with_suffix('.json').read_text())
            ready = path.stat().st_size == metadata['bytes']
        except (OSError, ValueError, KeyError):
            metadata, ready = {}, False
        packs.append({'system': name, 'available': ready, 'file': filename,
                      'start_utc': metadata.get('start_utc'), 'end_utc': metadata.get('end_utc')})
    return {'offline': True, 'satellite_packs': packs,
            'visual_model_installed': (MODEL / 'manifest.json').is_file() and (MODEL / 'model_quantized.onnx').is_file(),
            'visual_model_validated_accuracy': None}


@lru_cache(maxsize=8)
def verified_pack(path, size, modified_ns):
    metadata = json.loads(path.with_suffix('.json').read_text())
    with path.open('rb') as stream:
        digest = hashlib.file_digest(stream, 'sha256').hexdigest()
    if digest != metadata['sha256']:
        raise ValueError('Satellite ephemeris checksum mismatch: ' + path.name)
    return metadata


def solar_positions(site, include_status=False):
    path = ROOT / 'resources/de421.bsp'
    if not path.is_file():
        raise ValueError('Install the local DE421 ephemeris for moving-object identification.')
    from skyfield.api import load, load_file, wgs84
    with ExitStack() as resources:
        eph = load_file(str(path))
        resources.callback(eph.close)
        instant = load.timescale(builtin=True).from_datetime(site.utc)
        observer = (eph['earth'] + wgs84.latlon(site.latitude, site.longitude, elevation_m=site.elevation_m)).at(instant)
        records, warnings, loaded = [], [], {}
        for parent, (filename, barycenter, center) in PACKS.items():
            pack_path = ROOT / 'resources/ephemerides' / filename
            try:
                stat = pack_path.stat()
                meta = verified_pack(pack_path, stat.st_size, stat.st_mtime_ns)
                utc = site.utc.isoformat()
                # SPK can include interpolation padding; enforce advertised dates.
                if not (meta['start_utc'] <= utc < meta['end_utc']):
                    raise ValueError('outside installed 2025–2028 coverage')
                pack = load_file(str(pack_path))
                resources.callback(pack.close)
                loaded[parent] = (pack, eph[barycenter])
            except (OSError, ValueError, KeyError) as exc:
                warnings.append(f'{parent} satellite pack unavailable for this observation: {exc}')
        for name, key in BODIES.items():
            # Astrometric topocentric directions on ICRS/J2000 axes, matching
            # stellar WCS conventions. Do not relabel apparent GCRS as ICRS.
            vector = eph[key]
            reference = 'system barycenter' if 'barycenter' in key else 'body center'
            if name in loaded:
                pack, barycenter = loaded[name]
                vector = barycenter + pack[PACKS[name][2]]
                reference = 'body center'
            ra, dec, distance = observer.observe(vector).radec()
            records.append({'id': 'solar:' + name.lower(), 'name': name,
                            'kind': 'natural satellite' if name == 'Moon' else 'planet',
                            'ra_deg': ra.hours * 15, 'dec_deg': dec.degrees,
                            'distance_km': distance.km, 'position_reference': reference})
        for name, (target, parent) in SATELLITES.items():
            if parent not in loaded:
                continue
            pack, barycenter = loaded[parent]
            ra, dec, distance = observer.observe(barycenter + pack[target]).radec()
            records.append({'id': 'solar:' + name.lower(), 'name': name, 'kind': 'moon',
                            'parent': parent, 'ra_deg': ra.hours * 15, 'dec_deg': dec.degrees,
                            'distance_km': distance.km, 'position_reference': 'body center'})
        return (records, warnings) if include_status else records


def identify_field(solution, analysis, site):
    mapping = image_wcs(solution)
    predictions, warnings = solar_positions(site, include_status=True)
    records, xy = project_records(mapping, predictions, analysis['width'], analysis['height'])
    sources = np.array([[s['x'], s['y']] for s in analysis['sources']], dtype=float).reshape(-1, 2)
    matches, ambiguous = match_unique(xy, sources, 3)
    matched = {i: (j, d) for i, j, d in matches}
    results = []
    for i, record in enumerate(records):
        result = {**record, 'x': float(xy[i, 0]), 'y': float(xy[i, 1]), 'evidence': 'expected'}
        # A satellite projected on its parent's disk cannot be identified from a
        # bright centroid alone. Leave transits/occultations as expected locations.
        parent = next((p for p in predictions if p['name'] == record.get('parent')), None)
        blended = False
        if parent:
            from astropy.coordinates import SkyCoord
            from astropy import units as u
            separation = SkyCoord(record['ra_deg']*u.deg, record['dec_deg']*u.deg).separation(SkyCoord(parent['ra_deg']*u.deg, parent['dec_deg']*u.deg)).arcsec
            radius = {'Jupiter': 71492, 'Saturn': 60268}[parent['name']]
            radius_arcsec = np.degrees(np.arcsin(radius / parent['distance_km'])) * 3600
            pixel_arcsec = mapping.pixel_to_world(*xy[i]).separation(mapping.pixel_to_world(*(xy[i]+[1, 0]))).arcsec
            blended = separation <= radius_arcsec + 3 * pixel_arcsec
            if blended:
                result['association_warning'] = 'Near/on parent disk: transit, occultation or glare can prevent identification.'
        if i in matched and not blended and record['position_reference'] == 'body center':
            j, residual = matched[i]
            result.update(evidence='positional match', source_index=j, residual_px=round(residual, 3))
        results.append(result)
    return {'mode': 'field', 'status': 'ready', 'objects': results, 'ambiguous_count': ambiguous,
            'observation': site.model_dump(mode='json'), 'offline': True, 'resource_warnings': warnings,
            'message': 'Time-dependent local DE421 positions in the solved image. A positional coincidence is not a visual confirmation; expected locations are not detections.'}


def disk_box(rgb):
    """Locate a dominant bright region without assuming its astronomical identity."""
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    scale = min(1, 768 / max(gray.shape))
    small = cv2.resize(gray, None, fx=scale, fy=scale)
    if float(small.std()) < 2:
        return None
    _, mask = cv2.threshold(small, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    count, _, stats, _ = cv2.connectedComponentsWithStats(mask)
    # Horizons, white image borders and connected background noise are not
    # isolated disks. Reject regions reaching the edge or sparsely filling their
    # bounding box before the automatic router considers the close-up path.
    h, w = small.shape
    regions = [s for s in stats[1:] if s[4] >= max(100, small.size*.002)
               and s[0] > 1 and s[1] > 1
               and s[0]+s[2] < w-1 and s[1]+s[3] < h-1
               and s[4] / (s[2]*s[3]) >= .2]
    if not regions:
        return None
    x, y, width, height, area = max(regions, key=lambda s: s[4])
    if area > .85 * small.size:
        return None
    return [int(x / scale), int(y / scale), int(width / scale), int(height / scale)]


@lru_cache(maxsize=1)
def visual_model():
    import onnxruntime as ort
    from tokenizers import Tokenizer
    manifest = json.loads((MODEL / 'manifest.json').read_text())
    # Check integrity once per process before loading executable model graphs.
    for name in ('model_quantized.onnx', 'tokenizer.json', 'preprocessor_config.json'):
        path = MODEL / name
        with path.open('rb') as stream:
            actual = hashlib.file_digest(stream, 'sha256').hexdigest()
        if actual != manifest[name]['sha256']:
            raise ValueError('Local solar image model checksum differs from its manifest.')
    config = ort.SessionOptions()
    config.intra_op_num_threads = 2
    session = ort.InferenceSession(str(MODEL / 'model_quantized.onnx'), sess_options=config, providers=['CPUExecutionProvider'])
    tokenizer = Tokenizer.from_file(str(MODEL / 'tokenizer.json'))
    tokenizer.enable_truncation(max_length=77)
    tokenizer.enable_padding(length=77, pad_id=49407, pad_token='<|endoftext|>')
    encoded = tokenizer.encode_batch(PROMPTS)
    return session, np.array([e.ids for e in encoded], dtype=np.int64), np.array([e.attention_mask for e in encoded], dtype=np.int64), manifest


def classify_closeup(rgb):
    box = disk_box(rgb)
    if box is None:
        return {'mode': 'closeup', 'status': 'unknown', 'objects': [], 'offline': True,
                'message': 'No dominant resolved bright object found. Try the original close-up. A small bright dot does not identify a planet.'}
    x, y, width, height = box
    pad = max(8, int(max(width, height) * .15))
    crop = Image.fromarray(rgb).crop((max(0, x-pad), max(0, y-pad), min(rgb.shape[1], x+width+pad), min(rgb.shape[0], y+height+pad)))
    ratio = 224 / min(crop.size)
    crop = crop.resize((max(224, int(crop.width * ratio)), max(224, int(crop.height * ratio))), Image.Resampling.BICUBIC)
    left, top = (crop.width-224)//2, (crop.height-224)//2
    pixels = np.asarray(crop.crop((left, top, left+224, top+224)), dtype=np.float32) / 255
    pixels = ((pixels - [0.48145466, .4578275, .40821073]) / [.26862954, .26130258, .27577711]).transpose(2, 0, 1)[None].astype(np.float32)
    session, ids, masks, manifest = visual_model()
    supplied = {'input_ids': ids, 'attention_mask': masks, 'pixel_values': pixels}
    output = dict(zip([o.name for o in session.get_outputs()], session.run(None, {i.name: supplied[i.name] for i in session.get_inputs()})))
    # Raw cosine similarity is a ranking, not a calibrated probability.
    vision = output['image_embeds']; text = output['text_embeds']
    similarities = ((vision / np.linalg.norm(vision, axis=-1, keepdims=True)) @ (text / np.linalg.norm(text, axis=-1, keepdims=True)).T)[0]
    order = np.argsort(similarities)[::-1]
    winner = int(order[0]); gap = float(similarities[winner] - similarities[order[1]])
    suggested = winner < len(LABELS)-1 and similarities[winner] >= .24 and gap >= .012
    obj = {'name': 'Possible ' + LABELS[winner], 'id': 'visual:' + LABELS[winner].lower(),
           'x': x+width/2, 'y': y+height/2, 'evidence': 'visual suggestion'}
    return {'mode': 'closeup', 'status': 'suggestion' if suggested else 'unknown',
            'objects': [obj] if suggested else [], 'offline': True, 'disk_box': box,
            'ranking': [{'name': LABELS[int(i)], 'similarity': round(float(similarities[i]), 4)} for i in order[:3]],
            'model': {'source': manifest['source'], 'revision': manifest['revision']},
            'message': 'Experimental visual suggestion, not a plate solution or confirmed identity. Similar-looking planets, moons, edited pictures and artificial objects can be confused. No celestial coordinates are inferred.'}


class SolarRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    mode: Literal['closeup', 'field'] = 'closeup'
    solve_id: str | None = None
    observation: SiteRequest | None = None


def solar_router(prototype):
    router = APIRouter(prefix='/api/v1')
    visual_lock = Lock()

    @router.get('/solar/status')
    def status():
        return resource_status()

    @router.post('/images/{image_id}/solar-analysis')
    def analyze(image_id: str, request: SolarRequest):
        image = prototype.require('image', image_id)
        try:
            if request.mode == 'field':
                if request.observation is None or request.solve_id is None:
                    raise HTTPException(422, 'Supply the actual observation time/location and a successful star-field solve.')
                job = prototype.require('solve', request.solve_id)
                if job['image_id'] != image_id or job['status'] != 'solved':
                    raise HTTPException(409, 'A successful solve of this image is required. Close-ups without stars need visual analysis.')
                result = identify_field(job['solution'], image['analysis'], request.observation)
            else:
                if not visual_lock.acquire(blocking=False):
                    raise HTTPException(409, 'Another visual analysis is running.')
                try:
                    rgb, _, _ = decode_image((prototype.store.files / image['original']).read_bytes())
                    result = classify_closeup(rgb)
                finally:
                    visual_lock.release()
        except (OSError, ImportError) as exc:
            raise HTTPException(503, 'Local solar-model or ephemeris resources are unavailable. See docs/solar-system.md.') from exc
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc
        return prototype.store.new('solar-analysis', image_id=image_id, solve_id=request.solve_id, **result)

    @router.get('/images/{image_id}/solar-analysis')
    def latest(image_id: str):
        prototype.require('image', image_id)
        return prototype.store.latest_for_image('solar-analysis', image_id)

    return router
