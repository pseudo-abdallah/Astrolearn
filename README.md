# AstroLearn image-only software prototype

A working local application for the capstone workflow, using pictures you upload
until the camera and Raspberry Pi are available. **No webcam access is used.**

**Current debugging baseline:** new uploads and **Analyze again** perform a fresh
native solve; historical results are marked as saved. The Sources overlay reports
its candidate/display counts independently of star names. Start testing with
[the verified survey test pack](samples/plate-solving-test-set/README.md), or read
[the fresh-solving debug report](docs/fresh-solving-debug.md). The final run passed
66 regression tests and 11 fresh-pipeline benchmark checks (four independent
survey fields, derived variants and negative/synthetic controls).

The [offline-first plan](docs/offline-first-plan.md) records the agreed roadmap.
The [identification guide](docs/offline-identification.md) explains the implemented
offline names, matching evidence, local catalogs and limits.

The source document reviewed is `AstroLearn22222.docx (original project report, supplied separately)`,
especially Appendix A, Appendix B, and sections 2.2.2–2.2.3. Appendix A calls for
target-position calculation, a motor-command demonstration, emergency stopping,
and OpenCV source markers. This laptop version implements the software workflow
and adds real offline plate solving as requested. Physical motion and hardware
emergency stopping are explicitly simulated, not claimed as demonstrated.

## Open the prototype

From the project folder:

```powershell
.\.venv\Scripts\python.exe -m uvicorn astrolearn.main:app --host 127.0.0.1 --port 8000
```

Or double-click `Start-AstroLearn.cmd`. Keep the terminal open. Visit
[AstroLearn](http://127.0.0.1:8000/) for the application;
[/docs](http://127.0.0.1:8000/docs) is only the developer API reference.
If an older server is running, stop it with Ctrl+C before starting this version.

For a fresh installation with Python 3.11+:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
```

On Linux / Raspberry Pi OS, use `python3 -m venv .venv` and
`.venv/bin/python` instead of the Windows executable. Install the platform's venv
support first if necessary. Python 3.12 on Windows was used for validation here.
The fully resolved current environment is recorded in `requirements-lock.txt`;
the direct dependency lists are `requirements.txt` and `requirements-dev.txt`.
Local solver executables must match the operating system and CPU architecture.

## Try the complete picture workflow

1. Select **Betelgeuse** from the 23-object local catalog.
2. Confirm the manual site coordinates. Kuwait City is a demonstration default,
   not a GPS reading. Set the image observation time, or use current time for a demo.
3. Upload `samples/synthetic-orion-wide.png`. It is a clearly synthetic fixture,
   generated from the installed W08 star catalog, not an observed sky photograph.
4. Toggle **Mark sources** to inspect OpenCV's bright-source detections.
5. Set **image height / field of view** to **40°**, leave radius at **180°**,
   and click **Solve image locally**. No RA/DEC hints are required for this sample.
6. Calculate the target position to see RA, DEC, altitude and azimuth. Below-horizon
   targets remain usable for recorded-image analysis; the UI labels their visibility.
7. Inspect the real ASTAP solution and field-center angular offset. Add a note and
   click **Save observation**. Open **Saved observations** or export the JSON history.
8. Try a simulated RA or DEC step command, stop it, and reset the latched stop.
   These commands do not move any equipment.

The synthetic integration field recovered a center within about **0.039°** of
its known center. This verifies integration, not accuracy on real sky images,
physical acquisition, or the report's field-performance targets.

## What works now

- Responsive local interface, educational target content, night mode, image library.
- PNG, JPEG, TIFF and 2D FITS upload (20 MB / 24 megapixel limits), source markers,
  relative focus score, original image retention and generated previews.
- Offline Astropy coordinate transformations and local Skyfield / JPL DE421
  solar-system positions. Location and timezone-aware observation time are explicit.
- Real offline ASTAP plate solving in a background worker, progress polling,
  numeric search hints, bounded 120-second execution, and honest failure messages.
- Offline star identification using the full WCS and 41,411 local catalog stars
  (541 with names). Clickable labels and searchable details distinguish matches
  from expected star/Messier locations. Labels persist with saved observations;
  older solves need to be run again to generate their mappings and labels.
- Saved sessions tying the image, target, site, time, solve result and pointing
  offset together. Incompatible or unsolved results never become verified pointing.
- Persistent SQLite records, paginated history and image library, complete JSON export.
- A stateful mount simulator with axis steps, busy state, stop latch and explicit reset.
- A system architecture screen that explains the real and simulated components.

There is no star/planet identification neural network. OpenCV detections are bright
candidates, not verified stars. Focus score is a deterministic relative metric, not
a calibrated focus measurement or cloud classifier. Plate solving establishes the
image's field center; it does not prove the selected object is detected or tracked.

## Offline resources

The current workspace has ASTAP, W08, G05, D05 and D50 catalogs under `tools/astap/`, and
JPL `de421.bsp` under `resources/`. These large external binaries and catalogs are
ignored by Git; they are not downloaded when the application starts. Once installed,
normal application operation makes no external network requests.
The installed resource checksums are recorded in `resources/manifest.json`.

For another computer:

1. Obtain ASTAP for its OS from the [author's official downloads](https://www.hnsky.org/astap.htm).
   Put `astap_cli.exe` (Windows) or `astap_cli` (Linux) in `tools/astap/`. The full
   `astap.exe` / `astap` program is also supported.
2. Extract a matching star database into the same folder, or set `ASTAP_DATABASE`.
   W08 is for wide fields (20–80° image height); G05 covers approximately 3–20°.
   For narrower telescope images install D05, D20, D50 or D80 as appropriate.
   See the [database descriptions](https://sourceforge.net/projects/astap-program/files/star_databases/).
3. For solar-system calculations, put the [JPL DE421 ephemeris](https://ssd.jpl.nasa.gov/ftp/eph/planets/bsp/de421.bsp)
   in `resources/de421.bsp`. Its supported date range is limited (roughly 1900–2053).
   If absent, the app labels its approximate built-in Astropy fallback and disables
   solar-system pointing comparison because its returned frame differs.

Optional environment configuration before starting the server:

```powershell
$env:ASTAP_PATH = 'C:\path\to\astap_cli.exe'
$env:ASTAP_DATABASE = 'C:\path\to\star-database'
$env:ASTROLEARN_DB_PATH = 'data\astrolearn.sqlite3'
```

`.env` files are not loaded automatically. The image folder is beside the selected
database. No user account or cloud API key is needed.

Field of view means **image height in degrees**. Zero selects ASTAP's automatic
narrow-field search; it does not search every possible wide-angle field. Supply
the known height for wide-field images. A restricted radius needs both RA and DEC
hints; RA is degrees in this API and converted to hours for ASTAP internally.
An ordinary room image, isolated planet, Moon close-up or heavily edited starless
image will generally not plate solve. Use a focused star field and matching catalog.
For a failure, see [the troubleshooting guide](docs/plate-solving-troubleshooting.md).
The interface now shows input checks, installed catalog coverage, and a button
under optional hints to copy the selected target's coordinates as a search hint.
Calibrated FITS uploads also load their position and image height as unverified
search hints; a real star-pattern match is still required. New failed attempts
offer a downloadable native solver log. The supplied Altair image now solves
with Siril and the verified local Gaia catalog, and its central star is labeled
Altair. See [integration setup, usage and evidence](docs/integrations.md) for the
successful settings and measured limits.

## New offline and optional online features

The current interface has one **automatic image analysis** workflow. Adding an
image starts analysis; selecting a catalog target calculates its position and
sends it to the coordinate mount simulator. The System architecture and Saved
observations tabs have been removed. See [the automatic interface guide](docs/automatic-interface.md)
for controls, capture-time handling and the 60-test validation. Earlier guides
describe previous manual controls that are now combined.

The **Solar System analysis** panel now supports experimental local close-up
suggestions and time-dependent positions in star-solved fields. Small local JPL
excerpts add Io, Europa, Ganymede, Callisto and Titan for a bounded 2025–2027
interval. Read-only WebSocket telemetry is available. See [Solar System setup,
evidence levels and the 56-test validation](docs/solar-system.md).

For the next Solar System expansion, see the researched [camera benchmark,
planet/moon catalog and edge-AI plan](docs/solar-system-benchmark-edge-ai.md).
The new `scripts/make_camera_collection.py` generates reproducible camera-like
FITS test inputs and separate reference truth from local seed images. Eight
variants of the existing DSS reference were generated; these represent one
independent source, not a new real-world image collection.

The solver selector now supports **Automatic**, **ASTAP**, and **Siril**. This
laptop has both engines and their local resources installed. For a fresh Windows
checkout, `scripts/install_siril.py` performs the one-time Siril/Gaia download.
Automatic uses Siril first when position and scale hints are supplied, then
ASTAP; unknown fields use ASTAP's existing search. Runtime solving stays local.

Open **Sky & learning** for a local sky map and brightness CSV viewer. The map
uses your entered location/time; the viewer accepts `time,flux` CSV data, saves
imports locally, and includes an explicitly synthetic lesson. Select an object
in a solved image for local details and an optional SIMBAD update button. Cached
metadata remains available offline. Live SIMBAD access timed out during testing;
graceful failure and cached behavior are tested. GraXpert, Lightkurve, MAST/TESS
and the other research links are available as optional external learning tools.
They have not all been installed or embedded. See [the integration guide](docs/integrations.md)
for exact scope, APIs, provenance, and verification.

## Tests and architecture

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe scripts\verify_offline_solver.py
```

The automated integration tests run the real installed solvers when their resources
and sample images are present; otherwise those checks are explicitly skipped. Tests use
temporary databases and do not overwrite normal observation records. Re-create
the synthetic fixture with `scripts/make_demo_image.py` after installing W08.

See [design and requirement mapping](docs/design.md) and
[verification evidence](docs/verification.md). Backend modules contain explanatory
comments. The project is a local prototype with no authentication; keep it bound
to localhost. The browser UI substitutes for the final Flutter touchscreen named
in the report and uses the same REST API a Flutter client could consume.

The report's hardware results, 80% solve-success target, 0.1° reference-planetarium
agreement, 120-second acquisition, and 10-minute physical tracking are **not**
claimed by this laptop demonstration. Actual UART, GPS, homing, calibrated mount
corrections, physical PID tuning and independent E-stop verification require the
real equipment. AI, voice, cloud fallback, and autonomous tracking remain future
integration work. No live camera is requested or configured in this version.

## Repository development baseline

The working implementation is in `astrolearn/` (Python API and served UI) and
`user-app/` (standalone UI prototype). The other component folders describe planned
boundaries for future development. See [source import](docs/source-import.md) for
the imported baseline, excluded local assets, and setup limits. See also the
[architecture proposal](docs/architecture.md) and [work packages](docs/work-packages.md).
