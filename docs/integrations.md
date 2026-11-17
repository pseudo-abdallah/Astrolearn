# Offline astronomy integrations

Implemented and checked on November 2, 2026, on the Windows laptop. No telescope
hardware, camera, motor or GPS is assumed.

## What is working

| Component | Implementation | Internet during normal use |
|---|---|---|
| Siril 1.4.5 | Real local subprocess solver with the Gaia DR3 astrometric extract | No; launched with `--offline` and `-catalog=localgaia` |
| ASTAP | Existing solver, selectable explicitly or used by the automatic dispatcher | No |
| Sky map | Local catalog projected into altitude/azimuth using Astropy, displayed on a local canvas | No |
| Object details | Local image evidence plus persistent SIMBAD metadata cache | Only the explicit **Update details from SIMBAD** button requests data |
| Brightness viewer | CSV import, median normalization, local plot and SQLite persistence | No |
| Synthetic lesson | Bundled, explicitly simulated brightness measurements | No |
| External resources | Links to Siril, GraXpert, Lightkurve, MAST/TESS, exo.MAST, Cosmoscope, AstroViewer and teaching references | Yes, when you choose to open them |

The brightness viewer uses NumPy and the browser canvas. It does **not** import
the Lightkurve package or implement transit detection. The external websites are
not embedded or copied into the offline interface. GraXpert is linked as an
optional manual processing tool; its executable and AI weights are not installed.
No third-party notebook model has been added to the image-identification pipeline.

## Using the app

Open http://127.0.0.1:8000/ and refresh once after updating.

### Solve a photograph

Select an image from the library or upload a new one. Choose **Automatic**,
**ASTAP**, or **Siril** in the solver selector. Siril needs an approximate image
height, RA and DEC, or a calibrated FITS input. Automatic uses Siril first when
its resources and these hints are available, then tries ASTAP if Siril fails.
Without sufficient hints it uses ASTAP's existing search. It does not infer an
object's identity from the selected target. Each native invocation is limited to
120 seconds; an automatic attempt using both engines may take up to 240 seconds.

Siril runs in a fresh working directory, with an isolated config and a fresh FITS
array that contains **no input WCS**. `platesolve -force -noflip` requires a new
pixel-pattern match and preserves array orientation. Only a successful native
run with an actual celestial WCS enables labels. An existing FITS header is a
search hint, never proof. Both engines feed the same local catalog matcher and
observation/history APIs.

For the previously failing **512 × 511 Altair photograph**, the successful inputs
were Siril, image height seed **0.25°**, RA **297.6958°**, DEC **+8.8683°**, radius
**1°**. The seed is an approximate starting scale, not a camera specification.
Do not reuse these coordinates or scale for unrelated photographs.

The saved application result is solve `25750329c6fe48eb8e1a9f33d4541e20`, image
`af7f546ff95645e59802cc93718de38b`. It reports:

- Center RA **297.709735°**, DEC **+8.874678°**.
- Pixel scale **1.93634 arcsec/pixel**.
- **Altair / HIP 97649**, one unique positional catalog match, residual **1.377 px**.
- 331 other bright candidates remain unidentified; no names were invented for them.

The candidate detector now also measures the center of compact saturated regions
from the pixels. Background subtraction alone missed this star's flat white core.
This measurement is independent of catalog coordinates. Saturation still limits
precision; the label is a positional match, not a photometric or spectroscopic
confirmation. Existing image analysis is refreshed on the next solve; old saved
identification snapshots are retained.

### Explore the sky and brightness data

Open **Sky & learning** in the navigation. **Draw local sky** uses the observer
location and time from the Observation tab, showing catalog stars down to
magnitude 5 above the geometric horizon. Select a star to see its predicted
altitude/azimuth. North is up, east is left, and the center is the zenith. This
map is a prediction, not evidence about an uploaded photograph. It currently
shows stars, without constellation lines, planets or terrain/refraction modeling.

Import a UTF-8 CSV with `time,flux` headers, or try the synthetic lesson. Time
units remain those of the input; flux is divided by its positive median. The
importer accepts 3–10,000 finite measurements within 1 MB. **Restore latest data**
retrieves the last local import after restart. Dips alone do not prove a planet.
Exported archive measurements can be imported, but there is no automatic MAST
download, FITS light-curve import or Lightkurve analysis in this version.

### Optional online details

Select a matched or expected object in a solved image. Local details are shown
immediately. Previously saved SIMBAD details are read without internet. The
update button sends only that object's catalog identifier to the fixed SIMBAD
TAP endpoint; it sends no image, observer location, notes or account credentials.
The bounded query has an eight-second request timeout. A failure retains cached
details and the original image evidence. Expected objects remain expected after
enrichment; a database record cannot upgrade them to image detections.

SIMBAD's live endpoint timed out during this session. The query connector,
cache persistence and graceful failure path are implemented; a successful live
retrieval has **not** been verified here. Cached behavior was tested using an
explicit test fixture, not represented as live service data.

## Setup and provenance

This laptop has the official portable Siril program under `tools/siril/` and its
1,521,132,640-byte Gaia catalog under `resources/siril/gaia_astrometric.dat`.
These large resources are ignored by version control. The installer is an
explicit one-time online step:

```powershell
.\.venv\Scripts\python.exe scripts\install_siril.py
```

The program archive comes from the official Siril download link. The Gaia file
comes from [Zenodo record 14692304](https://zenodo.org/records/14692304), as linked
by the [Siril documentation](https://siril.readthedocs.io/en/stable/astrometry/platesolving.html).
The compressed Gaia SHA-256 was checked against the published value:
`846ad4b12c50865df0cb8c5b23453f22eec78bbe9969e17d669ae19eb49d421f`.
The extracted catalog SHA-256 is
`2fa40c93fe115235d35c5050757f2ef60a326a6f3030f87be1598c016fcb2388`.
`resources/siril-manifest.json` records the installation provenance and checksums.
The companion `.dat.json` completion marker prevents a partially extracted
catalog being advertised as ready. Status checks size/completion; full hashing
is performed during installation, rather than on every API request.

The setup script downloads the Windows portable build. On a future Linux/Pi
deployment, install a compatible native Siril executable and point `SIRIL_PATH`
at it; the Windows binary cannot run there. `SIRIL_GAIA_CATALOG` can select another
verified catalog path with its companion `.dat.json` manifest. The adapter also
sets pip/uv offline environment flags; Siril Python plugins are unnecessary for
this integration. No OS-level network capture or firewall-disconnected test was
performed, so the tests do not claim to audit every native process network call.

The real survey fixture `samples/altair-dss2-red-1deg.fits` was obtained from
[NASA SkyView](https://skyview.gsfc.nasa.gov/current/docs/batchpage.html), requesting
DSS2 Red, J2000 center 297.6958,+8.8683, 1° square, 1200 pixels, tangent projection.
Its original FITS provenance and copyright comments are preserved. It is a test
image, not a telescope capture by this project. The user-photo source was
[the supplied Altair page](https://www.star-facts.com/altair/altair-nasa-2/).

## API and code

| Route | Purpose |
|---|---|
| `GET /api/v1/prototype/status` | Installed engines and local catalog readiness |
| `POST /api/v1/images/{id}/solve` | Existing job API, now with `backend: auto/astap/siril` |
| `POST /api/v1/sky-map` | Site/time request → predicted visible bright stars |
| `GET /api/v1/solves/{id}/object-details?object_id=HIP%2097649` | Local/cache-only details |
| `POST` to the same object-details route | Explicit SIMBAD refresh |
| `POST /api/v1/lightcurves` | Raw CSV → normalized, saved measurements |
| `GET /api/v1/lightcurves` | Latest 20 local imports |

Implementation: `astrolearn/siril_solver.py`, `learning.py`, `imaging.py`,
`identification.py`, `static/learning.js` and the existing prototype APIs. Core
Python requirements did not change. Attribution for the existing identification
catalog remains in its resource manifest and license files.

## Validation

The final run passed **46 tests**. This includes real Siril/Gaia solves of a
normal and horizontally mirrored survey array with all input WCS stripped.
The returned mapping was compared at five image positions against independent
survey calibration, within 5 arcseconds in each parity. One direct survey solve
agreed within 1.7 arcseconds at those positions. Existing real ASTAP tests pass.
Python network entry points are blocked in offline integration tests; Siril is
invoked with its documented offline flag. Cache tests cover restart persistence,
service failure, and preservation of expected-versus-detected evidence.

The browser showed the new map (779 stars for the chosen site/time), a synthetic
201-point light curve, both engines ready, and the saved Altair solution and
matched name. Browser console checks reported no errors. Screenshots are saved
alongside this document. There is no claim of universal image-solving success,
exoplanet discovery, physical pointing accuracy or tracking validation.
