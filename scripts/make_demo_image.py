"""Render a deterministic synthetic star field from the installed W08 catalog.

This is a solver integration fixture, not an observed image or field-test result.
The gnomonic projection has a known center and no embedded WCS hints.
"""

from pathlib import Path
import sys

import cv2
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent


def main():
    source = ROOT / 'tools' / 'astap' / 'w08_0101.001'
    raw = source.read_bytes()
    stars = np.frombuffer(raw, dtype='<f4', offset=4).reshape(-1, 3)
    magnitude, ra, dec = stars.T
    ra0, dec0 = np.deg2rad([88.7929, 7.4071])
    delta = ra - ra0
    denominator = np.sin(dec0)*np.sin(dec) + np.cos(dec0)*np.cos(dec)*np.cos(delta)
    x = np.cos(dec)*np.sin(delta) / denominator
    y = (np.cos(dec0)*np.sin(dec) - np.sin(dec0)*np.cos(dec)*np.cos(delta)) / denominator
    height, width = 1200, 1600
    scale = height / (2*np.tan(np.deg2rad(40)/2))
    px, py = width/2 - x*scale, height/2 - y*scale
    valid = (denominator > 0) & (px>10) & (px<width-10) & (py>10) & (py<height-10) & (magnitude<75)
    image = np.full((height, width), 12.0, dtype=np.float32)
    for sx, sy, mag in zip(px[valid], py[valid], magnitude[valid]/10):
        ix, iy = int(round(sx)), int(round(sy))
        yy, xx = np.mgrid[iy-5:iy+6, ix-5:ix+6]
        amplitude = min(800, 60 * 10**(-0.25*(float(mag)-6)))
        image[iy-5:iy+6, ix-5:ix+6] += amplitude*np.exp(-((xx-sx)**2+(yy-sy)**2)/(2*1.3**2))
    image += np.random.default_rng(42).normal(0, 1, image.shape)
    out = ROOT / 'samples' / 'synthetic-orion-wide.png'
    out.parent.mkdir(exist_ok=True)
    Image.fromarray(np.clip(image, 0, 255).astype('uint8')).save(out)
    print(f'{out}: {valid.sum()} catalog sources; center RA 88.7929, DEC 7.4071; height 40 degrees')


if __name__ == '__main__':
    main()
