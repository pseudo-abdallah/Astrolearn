# AstroLearn plate-solving test set

Start with **pleiades-survey.fits**, then **vega-survey.fits**.

## Set A — automatic real survey tests

Open http://127.0.0.1:8000/ and add one `*-survey.fits` file. Do not enter a
catalog target or image hints. Wait for **Star field solved · fresh solve**.
These FITS files include approximate pointing/scale hints; the native solver
strips their existing mapping and matches the actual star pattern. This tests
hinted solving, rather than blind all-sky identification.

| File | Expected result |
| --- | --- |
| `pleiades-survey.fits` | Solved field; Alcyone, Atlas, Electra, Maia, Merope and other stars. M45 is an expected catalog location. |
| `vega-survey.fits` | Solved field and a positional match to Vega. |
| `andromeda-survey.fits` | Solved field; M31, M32 and M110 listed as expected catalog locations. No named-star match is required. |
| `orion-nebula-survey.fits` | Solved via corner stars; M42/M43 expected locations. A warning explains that positions outside the matched region may be less accurate. |

The final benchmark obtained center errors below 1 arcsecond for Vega, Pleiades
and Andromeda, and approximately 9 arcseconds for Orion's crop-based solution.
These are four independent survey fields, not a measured general success rate.

## Set B — the same real pixels as PNGs

The four `*-pixels.png` files have no pointing metadata. For a repeatable hinted
test, open **Image settings** and enter the exact RA, DEC, field height and search
radius recorded under `options` in `manifest.json`, then **Analyze again**.
The first automatic attempt may take up to two minutes and may fail without
hints; that is a different, blind-search test.

| PNG field | RA degrees | DEC degrees | Field height | Radius |
| --- | --- | --- | --- | --- |
| Vega | 279.2347 | 38.7837 | 1 degree | 2 degrees |
| Pleiades | 56.7500 | 24.1167 | 1 degree | 2 degrees |
| Andromeda | 10.6847 | 41.2690 | 1 degree | 2 degrees |
| Orion nebula | 83.8221 | -5.3911 | 1 degree | 2 degrees |

## Set C — blind and negative controls

- `synthetic-orion-wide.png`: leave every hint blank/default. The bounded scale
  search should solve it with ASTAP and match stars such as Rigel and Betelgeuse.
  This is a synthetic software-control image, not a real observation.
- `blank.png` and `random-noise.png`: neither may receive a successful WCS or
  confirmed object name. Finding bright candidates in noise is not a solve.

## Check the Sources control

With an image loaded, check **Sources** and uncheck **Names**. Green circles must
appear independently of a successful solve. The caption reports the candidate
count and how many strongest points are displayed; a display cap keeps small
screens readable. Toggle Sources off and the circles disappear. Candidates can
include artifacts and texture, so they are not automatically named stars.

## Reproduce all checks offline

From the project folder:

```powershell
.\.venv\Scripts\python.exe scripts/benchmark_solver_test_set.py --include-blind
```

The script uses a **new empty database** and `reuse_solution: false` for every
upload. It runs local Siril/Gaia or ASTAP, compares the recovered centers against
independent survey coordinates, rejects solutions for the negative controls,
and saves `results.json` plus per-image `diagnostics/`. The recorded run passed
**11/11 checks**: eight variants of four real fields, one synthetic control,
and two negatives. PNG variants are not additional independent observations.

## Provenance

Real pixels come from the STScI Digitized Sky Survey, DSS2 red. FITS files were
binned 2×2 where necessary to fit the app's upload limit; PNGs are stretched
display versions. Exact source URLs and SHA-256 values are in `manifest.json`.
Original headers are retained as `*-original-header.txt`, including survey
copyright/acknowledgment information; full originals also remain in `raw/` in the
project (excluded from the small ZIP).

- [DSS access documentation](https://stdatu.stsci.edu/dss/script_usage.html)
- [DSS copyright and acknowledgments](https://stdatu.stsci.edu/dss/copyright.html)
- [ASTAP search parameters](https://www.hnsky.org/astap.htm)
