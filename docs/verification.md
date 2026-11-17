# Image prototype verification

## Fresh-solving verification — November 3, 2026

66 regression tests pass. The independent survey/control benchmark passes 11/11
checks in a new empty database with result reuse disabled. Real fields: Vega,
Pleiades, Andromeda and Orion; FITS/PNG variants are not independent observations.
Browser upload and Analyze again both produced a fresh Pleiades solve with nine
proper names. Sources were checked on/off independently of Names, and screenshots
were saved. See [debug details](fresh-solving-debug.md) and
[test instructions](../samples/plate-solving-test-set/README.md).

## Merged routing regression — November 3, 2026

62 tests pass after correcting bright-border/horizon routing and recovering real
solutions for byte-identical re-uploads. The uploaded Canopus photo again shows
its verified name in the browser. Three landscape photos remain unsolved;
additional broad-scale trials did not establish a WCS. See
[the regression details](automatic-interface.md#image-routing-regression-fix).

## Automatic interface update — November 3, 2026

The full suite passed 60 tests after merging the image workflows and adding
target-to-simulator coordinate commands. The browser verified automatic Moon
analysis and Vega position/dispatch. System architecture and Saved observations
were removed from navigation. See [current interface behavior](automatic-interface.md).

## Solar System update — November 3, 2026

The final full run passed 56 tests, including real local visual-model execution,
JPL satellite prediction, date limits, field/WCS ownership checks, persistence,
blank-image rejection and WebSocket telemetry. The browser displayed **Possible
Moon**, the installed resource dates and live simulated-status telemetry without
console errors. These are functional checks, not recognition accuracy or moon
detection measurements. See [the current Solar System implementation](solar-system.md).

## Current integration result — November 2, 2026

The final suite passed 46 tests. Siril/Gaia solved the actual Altair upload and
the local matcher identified Altair/HIP 97649 at a 1.377-pixel residual after
saturated-core detection was added. Real survey-array tests verified normal and
mirrored WCS alignment. The browser map and brightness lesson were exercised
without console errors. The live SIMBAD service timed out; cache persistence and
failure behavior were tested. See [full integration evidence](integrations.md).
Earlier results below are retained as historical investigation records.

## Small-image solve troubleshooting

The 512 × 511 Altair-source photograph remained unsolved after adding the offline
D50 catalog and testing coordinate hints, automatic scale and diagnostic trial
scales. This is recorded as a failure, not a verified identity. The interface now
shows actionable input checks and database coverage, with a selected-target hint
button. All 34 automated tests passed. Details, exact limits and the native log
findings are in [plate-solving-troubleshooting.md](plate-solving-troubleshooting.md).

## Offline identification milestone

The expanded suite passed **33 tests** on November 2, 2026, including actual PNG
and mirrored FITS ASTAP solves with Python network calls blocked. The source
catalog contains 41,411 stars (541 named) and 110 Messier objects. WCS, unique
matching, ambiguity rejection, expected-object semantics, checksums, independent
target selection and restart persistence are covered. This is not an OS firewall
test of the native ASTAP process or a real-photograph accuracy study.

The browser also solved the included synthetic Orion PNG and displayed 1,140
matched stars, 30 named stars, and 6 expected Messier locations. Clicking
Betelgeuse showed HIP 27989, a 0.20-pixel residual and its catalog coordinates.
Full details and limitations are in [offline-identification.md](offline-identification.md).
After refreshing the browser, reopening the image restored its saved names without
another solve. A labeled synthetic observation was saved. Searching for M42 showed
the explicit expected-location / not-confirmed-detection message. The browser
reported no console errors or warnings. Screenshot: `docs/offline-labels-preview.png`.

Verified November 2, 2026 on Windows with Python 3.12.14.

## Automated checks

Command: `.venv/Scripts/python.exe -m pytest -q --tb=short`

**26 tests passed**, including a real ASTAP solve and saved pointing comparison.
One upstream Starlette/AnyIO deprecation warning remains. `python -m pip check`
reported no broken requirements. JavaScript passed `node --check`.

The tests cover original foundation APIs plus invalid image rejection, preview
retrieval, missing resources, FITS handling, OpenCV source detection, manual site
validation, timezone requirements, local planetary ephemeris, simulated motion,
latched stop/reset, unsolved session persistence, export, malformed solver output,
solver failure/retry, real background solving and image/solution ownership checks.
Normal Windows access was needed for temporary files and the ASTAP subprocess.

## Real solver integration

`scripts/make_demo_image.py` projects 1,522 W08 catalog entries into a deterministic
synthetic 1600 × 1200 PNG, with image height 40° and center RA 88.7929°, DEC 7.4071°.
The image contains no embedded WCS hints. The real local ASTAP binary solved it
with a 180° search radius and no pointing hint, returning:

- RA: 88.83201724495082°
- DEC: 7.404157417698186°
- Pixel scale: 124.99037939176597 arcseconds / pixel
- Rotation: −0.1258962705155322°
- Great-circle center error: about 0.038902°

These are synthetic integration results, not real sky validation or physical
telescope accuracy. The automated API test uploads that image, starts the real
background solver, polls completion and saves the resulting target comparison.

## Browser checks

The updated app was opened at `http://127.0.0.1:8000/`. The included synthetic
image was selected through the actual file chooser, uploaded, previewed and
marked with 1,425 OpenCV candidates. Betelgeuse was selected, site/time coordinates
were calculated, and a real solve was launched in the UI with field height 40°.
The browser showed **Solved**, RA 88.83202°, DEC 7.40416°, and pointing offset 0.0389°.
A demonstration observation was saved with notes explicitly identifying it as
synthetic, not an observed photograph or tracking test.
The history screen showed that saved record, and the browser reported no console
errors or warnings. A screenshot is saved as `docs/prototype-preview.png`.
ASTAP plus W08, G05 and D05 were installed locally; resource checksums are in
`resources/manifest.json`. The final regression run again passed all 26 tests.

## Scope limits

The supplied capstone DOCX was read, including its prototype procedure and
software architecture. The earlier PDF retrieval gap is superseded by that source.
No Raspberry Pi, camera, GPS, ESP32, real motor, independent emergency stop or
physical tracking was tested. No reference planetarium comparison or multi-image
clear-sky success study has been performed. Those requirements remain unverified.
