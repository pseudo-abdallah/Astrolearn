"""Inspect one local image with ASTAP's own extractor, without uploading it."""

from pathlib import Path
import subprocess
import sys

import numpy as np
from astropy.io import fits
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from astrolearn.solver import AstapSolver

image = Path(sys.argv[1]).resolve()
folder = ROOT / 'tmp' / 'diagnostics' / image.stem
folder.mkdir(parents=True, exist_ok=True)
source = folder / 'input.fits'
with Image.open(image) as raster:
    fits.PrimaryHDU(np.asarray(raster.convert('L'))).writeto(source, overwrite=True)
solver = AstapSolver()
result = subprocess.run([str(solver.executable), '-f', str(source), '-extract', '10', '-log'],
    capture_output=True, text=True, timeout=30,
    creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0)
print('Extractor exit code:', result.returncode)
print('Output:', result.stdout[-1500:], result.stderr[-500:])
for file in folder.glob('*'):
    print(file.name, file.stat().st_size)
    if file.suffix in {'.log', '.csv', '.ini'}:
        text = file.read_text(errors='replace')
        print('Lines:', len(text.splitlines()), '\n', '\n'.join(text.splitlines()[:7]))
