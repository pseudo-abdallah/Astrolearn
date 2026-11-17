"""Offline catalog projection and conservative positional source matching.

An object inside a solved frame is expected, not automatically detected. Only
one-to-one star/source coincidences inside a small pixel radius are called matches.
No target choice, network lookup or image classifier supplies these identities.
"""

from functools import lru_cache
import hashlib
import json
from pathlib import Path

import numpy as np
from astropy.io import fits
from astropy.wcs import WCS, NoConvergence

DATA = Path(__file__).parent / 'data' / 'identification'
MATCH_RADIUS_PX = 3.0
MAX_RETURNED_MATCHES = 300
IDENTIFICATION_VERSION = 2


@lru_cache(maxsize=4)
def load_catalog(directory: Path):
    raw = (directory / 'catalog.json').read_bytes()
    manifest = json.loads((directory / 'manifest.json').read_text(encoding='utf-8'))
    if hashlib.sha256(raw).hexdigest() != manifest['catalog_sha256']:
        raise ValueError('Identification catalog checksum differs from its manifest. Reinstall the resource pack.')
    content = json.loads(raw)
    return content, manifest


@lru_cache(maxsize=4)
def load_deep_sky(directory: Path):
    """Load the separately licensed NGC/IC supplement, when installed."""
    manifest_path = directory / 'openngc-manifest.json'
    if not manifest_path.is_file():
        return [], None
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    raw = (directory/'openngc.json').read_bytes()
    if hashlib.sha256(raw).hexdigest() != manifest['catalog_sha256']:
        raise ValueError('OpenNGC catalog checksum mismatch.')
    return json.loads(raw), manifest


def image_wcs(solution: dict) -> WCS:
    if not solution.get('wcs_header'):
        raise ValueError('This solve has no full image mapping. Solve the image again to enable labels.')
    header = fits.Header.fromstring(solution['wcs_header'], sep='\n')
    mapping = WCS(header, naxis=2).celestial
    if not mapping.has_celestial or not np.isfinite(mapping.pixel_scale_matrix).all():
        raise ValueError('Invalid celestial WCS; no labels can be assigned.')
    if abs(np.linalg.det(mapping.pixel_scale_matrix)) < 1e-15:
        raise ValueError('Singular WCS; no labels can be assigned.')
    return mapping


def project_records(mapping, records, width, height):
    if not records:
        return [], np.empty((0, 2))
    ra = np.asarray([r['ra_deg'] for r in records])
    dec = np.asarray([r['dec_deg'] for r in records])
    # Astropy origin=0 means the same column/row convention as NumPy and canvas.
    with np.errstate(invalid='ignore', divide='ignore'):
        try:
            x, y = mapping.all_world2pix(ra, dec, 0)
        except NoConvergence as exc:
            pixels = exc.best_solution.copy()
            for indices in (exc.divergent, exc.slow_conv):
                if indices is not None:
                    pixels[indices] = np.nan
            x, y = pixels.T
    valid = np.isfinite(x) & np.isfinite(y) & (x >= 0) & (x < width) & (y >= 0) & (y < height)
    indices = np.flatnonzero(valid)
    return [records[i] for i in indices], np.column_stack((x[valid], y[valid]))


def match_unique(projected: np.ndarray, sources: np.ndarray, radius: float):
    """Bounded-memory, two-sided uniqueness check; blends remain unidentified."""
    if not len(projected) or not len(sources):
        return [], 0
    nearest = np.empty(len(projected), dtype=int)
    nearest_distance = np.empty(len(projected))
    candidates_per_star = np.zeros(len(projected), dtype=int)
    candidates_per_source = np.zeros(len(sources), dtype=int)
    for start in range(0, len(projected), 128):
        chunk = projected[start:start + 128]
        distances = ((chunk[:, None, :] - sources[None, :, :]) ** 2).sum(axis=2)
        inside = distances <= radius ** 2
        candidates_per_star[start:start + len(chunk)] = inside.sum(axis=1)
        candidates_per_source += inside.sum(axis=0)
        chosen = distances.argmin(axis=1)
        nearest[start:start + len(chunk)] = chosen
        nearest_distance[start:start + len(chunk)] = np.sqrt(distances[np.arange(len(chunk)), chosen])
    pairs = [(i, int(nearest[i]), float(nearest_distance[i])) for i in range(len(projected))
             if candidates_per_star[i] == 1 and candidates_per_source[nearest[i]] == 1]
    return pairs, int((candidates_per_source > 1).sum())


def magnitude_key(item):
    value = item.get('magnitude')
    return float(value) if isinstance(value, (int, float)) else 99.0


class OfflineIdentifier:
    def __init__(self, directory: Path = DATA):
        self.directory = directory

    def status(self):
        try:
            _, manifest = load_catalog(self.directory)
            extra, _ = load_deep_sky(self.directory)
            return {'available': True, 'offline': True, 'star_count': manifest['star_count'],
                    'named_star_count': manifest['named_star_count'], 'object_count': manifest['object_count'],
                    'ngc_ic_object_count': len(extra),
                    'revision': manifest['revision'], 'message': 'Local identification catalog ready'}
        except (OSError, ValueError, KeyError) as exc:
            return {'available': False, 'offline': True, 'message': str(exc)}

    def identify(self, solution: dict, analysis: dict):
        mapping = image_wcs(solution)
        catalog, manifest = load_catalog(self.directory)
        width, height = analysis['width'], analysis['height']
        stars, projected = project_records(mapping, catalog['stars'], width, height)
        detections = np.asarray([[s['x'], s['y']] for s in analysis['sources']], dtype=float).reshape(-1, 2)
        # Very large clipped photographic cores have a less precise intensity
        # centroid. Use a declared 6px limit for those alone, with the same
        # mutual-uniqueness/blend rejection; compact candidates remain at 3px.
        pairs, ambiguous = match_unique(projected, detections, 6)
        matches, matched_indices = [], set()
        for star_index, detection_index, distance in pairs:
            source = analysis['sources'][detection_index]
            large_clipped = source.get('profile') == 'saturated candidate' and source.get('area', 0) >= 10000
            radius = 6 if large_clipped else MATCH_RADIUS_PX
            if distance > radius:
                continue
            matched_indices.add(star_index)
            record = stars[star_index]
            cx, cy = detections[detection_index]
            # Angular separation at the actual source, including projection,
            # is more informative than using a global pixel-scale estimate.
            detected = mapping.pixel_to_world(float(cx), float(cy))
            expected = mapping.pixel_to_world(*projected[star_index])
            matches.append({**record, 'evidence': 'matched', 'x': float(cx), 'y': float(cy),
                            'catalog_x': float(projected[star_index, 0]), 'catalog_y': float(projected[star_index, 1]),
                            'source_index': detection_index, 'residual_px': round(distance, 3),
                            'match_radius_px': radius,
                            'source_profile': analysis['sources'][detection_index].get('profile', 'compact candidate'),
                            'separation_arcsec': round(float(detected.separation(expected).arcsec), 3)})
        matches.sort(key=lambda r: (not r.get('proper_name', False), magnitude_key(r), r['id']))
        expected_stars = [{**r, 'evidence': 'expected', 'x': float(projected[i, 0]), 'y': float(projected[i, 1])}
                          for i, r in enumerate(stars) if i not in matched_indices and r.get('proper_name')]
        expected_stars.sort(key=magnitude_key)
        extra, deep_sky_catalog = load_deep_sky(self.directory)
        objects, object_pixels = project_records(mapping, catalog['objects'] + extra, width, height)
        expected_objects = [{**r, 'evidence': 'expected', 'x': float(pixel[0]), 'y': float(pixel[1])}
                            for r, pixel in zip(objects, object_pixels)]
        expected_objects.sort(key=lambda r: (not bool(r.get('common_name') or r['id'].startswith('M')), magnitude_key(r)))
        return {'status': 'ready', 'offline': True, 'matched_star_count': len(matches),
                'identification_version': IDENTIFICATION_VERSION, 'deep_sky_catalog': deep_sky_catalog,
                'named_match_count': sum(r.get('proper_name', False) for r in matches),
                'unidentified_source_count': len(detections) - len(matches), 'ambiguous_source_count': ambiguous,
                'match_radius_px': MATCH_RADIUS_PX, 'matched_stars': matches[:MAX_RETURNED_MATCHES],
                'large_saturated_match_radius_px': 6,
                'matches_truncated': len(matches) > MAX_RETURNED_MATCHES,
                'expected_stars': expected_stars[:100], 'expected_objects': expected_objects,
                'catalog': {key: manifest[key] for key in ('source', 'revision', 'license', 'reference_frame')},
                'message': 'Names are positional catalog matches, not AI guesses. Expected objects are not confirmed detections.'}
