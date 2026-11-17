"""Run the real installed ASTAP on the documented synthetic integration image."""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from astrolearn.solver import AstapSolver, SolveOptions
from astropy.coordinates import SkyCoord
from astropy import units as u

solution = AstapSolver().solve(ROOT / 'samples' / 'synthetic-orion-wide.png', SolveOptions(fov_deg=40))
expected = SkyCoord(88.7929*u.deg, 7.4071*u.deg)
actual = SkyCoord(solution['ra_deg']*u.deg, solution['dec_deg']*u.deg)
error = actual.separation(expected).deg
print(solution)
print(f'Known synthetic center error: {error:.6f} degrees')
assert error < 0.1, 'Synthetic field was not recovered accurately'
