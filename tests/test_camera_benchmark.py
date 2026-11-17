import numpy as np
import pytest
from astropy.io import fits
import json

from astrolearn.camera_benchmark import CameraProfile, simulate, build_collection


def test_camera_noise_reproducible_and_input_unchanged():
    scene = np.zeros((80, 100), dtype=np.float32)
    scene[40, 50] = 1
    original = scene.copy()
    p = CameraProfile('test', hot_pixels=2)
    a = simulate(scene, p, seed=7)
    assert np.array_equal(a, simulate(scene, p, seed=7))
    assert not np.array_equal(a, simulate(scene, p, seed=8))
    assert np.array_equal(scene, original)
    assert a.dtype == np.uint16 and a.max() <= 4095
    with pytest.raises(ValueError):
        simulate(scene, CameraProfile('bad', gain_electrons_per_adu=0))


def test_truth_separate_and_translation_updated(tmp_path):
    header = fits.Header({'CRPIX1': 50., 'CRPIX2': 40.})
    seed = tmp_path / 'seed.fits'
    fits.writeto(seed, np.ones((80, 100)), header)
    output = build_collection(seed, tmp_path / 'collection', 'https://example.test/source', 'session-A')
    manifest = json.loads(output.read_text())
    assert manifest['independent_source_count'] == 1 and len(manifest['frames']) == 8
    drift = next(f for f in manifest['frames'] if f['profile']['name'] == 'tracking_trail')
    assert 'CRPIX1' not in fits.getheader(output.parent / drift['image'])
    truth = fits.Header.fromstring((output.parent / drift['truth']).read_text(), sep='\n')
    assert truth['CRPIX1'] == 58 and truth['CRPIX2'] == 35
    assert all(f['group_id'] == 'session-A' for f in manifest['frames'])
