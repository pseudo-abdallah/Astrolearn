"""Deterministic camera-like degradations, without assuming real camera specs.

These are relative signal simulations, not calibrated exposures or new independent
observations. Keep every derivative of one original in the same evaluation split.
"""

from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path

import cv2
import numpy as np
from astropy.io import fits
from PIL import Image


@dataclass(frozen=True)
class CameraProfile:
    name: str
    peak_electrons: float = 4000
    background_electrons: float = 30
    read_noise_electrons: float = 3
    gain_electrons_per_adu: float = 1.5
    blur_sigma_px: float = 0
    shift_x_px: int = 0
    shift_y_px: int = 0
    trail_px: int = 1
    hot_pixels: int = 0


PROFILES = [CameraProfile('nominal'), CameraProfile('low_signal', peak_electrons=300),
            CameraProfile('defocus', blur_sigma_px=2),
            CameraProfile('high_background', background_electrons=500, read_noise_electrons=12),
            CameraProfile('saturation', peak_electrons=18000),
            CameraProfile('tracking_trail', trail_px=9, shift_x_px=8, shift_y_px=-5),
            CameraProfile('hot_pixels', hot_pixels=150),
            CameraProfile('combined', peak_electrons=500, blur_sigma_px=1.5, trail_px=5, hot_pixels=75)]


def simulate(scene, profile: CameraProfile, seed=42):
    if scene.ndim != 2 or scene.size == 0 or not np.isfinite(scene).all():
        raise ValueError('Use a finite nonempty monochrome scene.')
    p = profile
    if p.gain_electrons_per_adu <= 0 or min(p.peak_electrons, p.background_electrons, p.read_noise_electrons, p.blur_sigma_px, p.hot_pixels) < 0 or p.trail_px < 1:
        raise ValueError('Invalid camera simulation parameters.')
    signal = np.maximum(scene.astype(np.float32), 0)
    maximum = float(signal.max())
    if maximum:
        signal /= maximum
    if p.blur_sigma_px:
        signal = cv2.GaussianBlur(signal, (0, 0), p.blur_sigma_px)
    if p.trail_px > 1:
        kernel = np.ones((1, p.trail_px), np.float32) / p.trail_px
        signal = cv2.filter2D(signal, -1, kernel)
    matrix = np.array([[1, 0, p.shift_x_px], [0, 1, p.shift_y_px]], dtype=np.float32)
    signal = cv2.warpAffine(signal, matrix, (scene.shape[1], scene.shape[0]))
    rng = np.random.default_rng(seed)
    electrons = rng.poisson(signal * p.peak_electrons + p.background_electrons).astype(float)
    electrons += rng.normal(0, p.read_noise_electrons, scene.shape)
    adu = electrons / p.gain_electrons_per_adu + 100
    if p.hot_pixels:
        locations = rng.choice(adu.size, min(p.hot_pixels, adu.size), replace=False)
        adu.flat[locations] = 4095
    return np.clip(adu, 0, 4095).astype(np.uint16)


def build_collection(source: Path, destination: Path, source_url: str, group: str):
    raw = source.read_bytes()
    parent_hash = hashlib.sha256(raw).hexdigest()
    if source.suffix.lower() in {'.fits', '.fit', '.fts'}:
        scene, header = fits.getdata(source, header=True)
    else:
        with Image.open(source) as image:
            scene = np.asarray(image.convert('L'))
        header = fits.Header()
    if scene.ndim != 2 or scene.size > 24_000_000:
        raise ValueError('Use a two-dimensional seed up to 24 megapixels.')
    destination.mkdir(parents=True, exist_ok=True)
    manifest = {'schema': 1, 'parent_sha256': parent_hash, 'source_url': source_url,
                'group_id': group, 'independent_source_count': 1,
                'warning': 'Simulated derivatives of one source; not independent real camera captures.', 'frames': []}
    for i, profile in enumerate(PROFILES):
        name = hashlib.sha256(f'{parent_hash}:{profile.name}'.encode()).hexdigest()[:16]
        frame = destination / (name + '.fits')
        # No celestial hints are written into the solver input.
        fits.writeto(frame, simulate(scene, profile, seed=42+i), overwrite=True)
        truth = header.copy()
        if 'CRPIX1' in truth:
            truth['CRPIX1'] += profile.shift_x_px
            truth['CRPIX2'] += profile.shift_y_px
        truth_file = destination / (name + '.truth.txt')
        truth_file.write_text(truth.tostring(sep='\n', padding=False))
        manifest['frames'].append({'image': frame.name, 'truth': truth_file.name,
            'profile': asdict(profile), 'seed': 42+i, 'group_id': group,
            'sha256': hashlib.sha256(frame.read_bytes()).hexdigest()})
    output = destination / ('manifest-' + parent_hash[:12] + '.json')
    output.write_text(json.dumps(manifest, indent=2))
    return output
