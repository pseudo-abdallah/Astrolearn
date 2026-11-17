"""Download four independent DSS survey fields and prepare reproducible tests.

Network is used only by --download. Runtime plate solving stays offline.
Original survey files, reference mappings and checksums are retained; no model
training or image-name lookup is involved. Derived images are not independent
observations. Negative controls must never receive a successful WCS.
"""
from pathlib import Path
import argparse
import hashlib
import json
import sys
import os
import shutil
import subprocess
import urllib.parse
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import numpy as np
from astropy.io import fits
from astropy.wcs import WCS
from PIL import Image
from astrolearn.imaging import decode_image

FIELDS = [('vega', 279.2347, 38.7837), ('pleiades', 56.75, 24.1167),
          ('andromeda', 10.6847, 41.269), ('orion-nebula', 83.8221, -5.3911)]


def prepare(download=False):
    root = ROOT/'samples/plate-solving-test-set'
    (root/'raw').mkdir(parents=True, exist_ok=True)
    cases = []
    for name, ra, dec in FIELDS:
        query = urllib.parse.urlencode(dict(v='poss2ukstu_red', r=ra, d=dec,
            e='J2000', h=60, w=60, f='fits', c='none'))
        url = 'https://archive.stsci.edu/cgi-bin/dss_search?'+query
        raw = root/'raw'/f'{name}-dss.fits'
        if not raw.exists() or raw.stat().st_size == 0:
            if not download:
                raise SystemExit('Missing survey files. Run once with --download.')
            print('Downloading', name, flush=True)
            if os.name == 'nt' and shutil.which('curl.exe'):
                # Windows curl validates against the OS certificate store.
                subprocess.run(['curl.exe','--fail','--location','--silent','--show-error',
                    '--max-time','90','--output',str(raw),url],check=True)
                data = raw.read_bytes()
            else:
                with urllib.request.urlopen(url, timeout=90) as response:
                    data = response.read(40*1024*1024)
            if not data.startswith(b'SIMPLE  ='):
                raise ValueError('DSS returned a non-FITS response for '+name)
            raw.write_bytes(data)
        array, header = fits.getdata(raw, header=True)
        (root/f'{name}-original-header.txt').write_text(header.tostring(sep='\n',padding=False))
        reference = WCS(header).celestial
        h, w = array.shape
        center = reference.pixel_to_world((w-1)/2, (h-1)/2).icrs
        height = reference.pixel_to_world((w-1)/2, -.5).separation(
            reference.pixel_to_world((w-1)/2, h-.5)).deg
        options = dict(ra_deg=float(center.ra.deg), dec_deg=float(center.dec.deg),
                       fov_deg=float(height), radius_deg=2)
        # A compact FITS with an explicit approximate pointing/scale seed. The
        # native solver strips existing WCS and still matches the pixel pattern.
        # 60-arcminute DSS originals can exceed the app's 20 MB upload limit.
        # Bin 2x2 (rather than dropping pixels) for a camera-like 1800px image.
        if max(array.shape) > 2000:
            bh, bw = (array.shape[0]//2)*2, (array.shape[1]//2)*2
            array = array[:bh,:bw].astype('float32').reshape(bh//2,2,bw//2,2).mean(axis=(1,3))
            h, w = array.shape
        seed = WCS(naxis=2)
        seed.wcs.crpix = [(w+1)/2, (h+1)/2]
        seed.wcs.crval = [center.ra.deg, center.dec.deg]
        seed.wcs.cdelt = [-height/h, height/h]
        seed.wcs.ctype = ['RA---TAN', 'DEC--TAN']
        seeded = root/f'{name}-survey.fits'
        seeded_header = seed.to_header()
        for card in header.cards:
            if card.keyword in {'COMMENT','HISTORY','ORIGIN','TELESCOP','INSTRUME','DATE-OBS','OBSERVER'}:
                seeded_header.append(card)
        fits.writeto(seeded, array, seeded_header, overwrite=True)
        rgb, _, _ = decode_image(seeded.read_bytes())
        png = root/f'{name}-pixels.png'
        Image.fromarray(rgb).save(png)
        for path, mode in [(seeded, 'automatic'), (png, 'manual-hints')]:
            cases.append(dict(file=path.name, field=name, type='real DSS survey',
                source_url=url, sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                expected='solved', expected_ra_deg=float(center.ra.deg),
                expected_dec_deg=float(center.dec.deg), tolerance_deg=.02,
                workflow=mode, options={} if mode=='automatic' else options))
    for name, pixels in [('blank.png', np.zeros((768,768), dtype='uint8')),
                         ('random-noise.png', np.random.default_rng(52).integers(0,256,(768,768),dtype='uint8'))]:
        Image.fromarray(pixels).save(root/name)
        cases.append(dict(file=name, type='negative control', expected='unsolved', options={}))
    manifest = dict(independent_survey_fields=len(FIELDS),
        source='STScI Digitized Sky Survey, DSS2 red', cases=cases)
    (root/'manifest.json').write_text(json.dumps(manifest, indent=2))
    wide = ROOT/'samples/synthetic-orion-wide.png'
    if wide.exists():
        shutil.copyfile(wide,root/wide.name)
    print(root, flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--download', action='store_true')
    prepare(parser.parse_args().download)
