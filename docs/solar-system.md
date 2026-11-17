# Solar System image analysis — implemented November 3, 2026

The prototype now has two separate local analysis paths. They share the image
library, can be restored after restart, and are included as snapshots when an
observation is saved. No camera, Pi, GPS or physical motor is assumed.

## How to use it

Open http://127.0.0.1:8000/ and refresh. Add an image, then find **Solar System
analysis** below the plate-solving controls.

**Close-up without background stars:** choose **Analyze close-up locally**.
The local CLIP/ONNX model ranks candidate planet/Moon appearances. A sufficiently
separated result is displayed as **Possible Moon**, **Possible Jupiter**, etc.
Otherwise the result is **Unknown close-up**. The label overlay is purple and
explicitly says “Possible”. No RA/DEC, successful WCS or confirmed detection is
created. The selected target and current time are not inputs to this classifier.

The initial model is a generic zero-shot baseline, not an astronomy-trained or
calibrated model. Raw cosine similarities are shown in an expandable panel and
are **not confidence probabilities**. Fixed acceptance thresholds are experimental.
Small dots, similar-looking moons/planets, artificial objects, edited images,
unusual filters and partial/cropped disks can be misclassified. Rejecting an
image is valid. The model does not identify Io versus Europa from appearance.

**Wider image with background stars:** solve the star field first using ASTAP or
Siril. Enter the actual image observation time and observer location in the
observer settings, confirm them in the Solar System panel, then choose **Check
bodies in solved field**. Download/publication time and the current clock are not
substitutes for the image's exposure time.

The app predicts moving bodies using local JPL data, projects them into the
verified WCS, and compares those positions with measured candidates. A unique
coincidence within 3 pixels is a **positional match**, not visual/spectroscopic
confirmation. Other bodies remain **expected** and are hidden from the overlay
unless **Expected locations** is enabled. Barycenter-only predictions are not
promoted to positional body-center matches. Moons near/on a projected parent disk
remain expected because a centroid cannot distinguish glare, transit or occultation.
The Saturn guard uses its equatorial body radius and does not model ring obscuration.

If no supported body falls in the field, the app says so. A close-up without a
successful stellar WCS cannot use this positional route; naming a target or
reading an unverified FITS header does not bypass that requirement.

## Installed offline scope

The local predictor returns up to **13 bodies**:

- Mercury, Venus, Mars, Jupiter, Saturn, Uranus and Neptune.
- Earth's Moon.
- Io, Europa, Ganymede, Callisto and Titan.

The main target selector also now includes Uranus and Neptune. The five additional
moons are handled in the Solar System analysis panel, rather than the main target
dropdown. Uranus/Neptune use system-barycenter approximations here; no dedicated
outer-planet body-center kernels were installed. The existing target-position
sidebar still uses its DE421 system-barycenter directions for the giant planets;
the new Solar System field analysis uses the Jupiter/Saturn body-center excerpts.

Jupiter/Saturn excerpts cover observations from **2025-01-02 00:00 UTC up to,
but excluding, 2027-12-31 00:00 UTC**. They were extracted for 2025-01-01 through
2028-01-01; the public interval retains a one-day light-travel-time safety margin.
Out-of-range/missing packs produce warnings and omit unsupported moons. There is
no automatic network download. These limits do not restrict visual-only analysis,
which does not compute a sky position.

The Jupiter/Saturn body-relative segments are combined with DE421 barycenter and
observer vectors. This is suitable for a prototype, but combining kernel families
has not been independently validated here against Horizons to a stated accuracy.
Do not claim professional astrometric precision or a moon-detection success rate.

## Resource provenance and setup

`resources/satellite-manifest.json` records local filenames, sources, hashes and
coverage. The installed excerpts total **1,745,000 bytes**:

- JUP365, targets 501–504 and 599: 1,373,856 bytes.
- SAT441L, targets 606 and 699: 371,144 bytes.

Sources are the [JPL satellite ephemeris table](https://ssd.jpl.nasa.gov/sats/ephem/files.html).
The extraction uses `jplephem` HTTP range requests as documented by
[Skyfield](https://rhodesmill.org/skyfield/planets.html#making-an-excerpt-of-an-ephemeris).
Checksums are verified before loading the excerpts. Status checks completion and
size; each distinct file's full digest is checked when first used in a process.

The visual model is the pinned ONNX conversion
`Xenova/clip-vit-base-patch32`, revision
`6b7c523703ae26e39be4b03774966f8571c7f523`. Its local graph is 153,695,702 bytes.
`resources/solar-model-manifest.json` records the pinned revision and resource
hashes; the graph, tokenizer and image preprocessing config are checked before
loading. Inference uses local files and ONNX Runtime's CPU provider. No remote
inference API is called. No Raspberry Pi latency, RAM or thermal benchmark has
been performed. Large resources are ignored by version control.

For a new checkout, these are explicit **online preparation** steps:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe scripts\install_satellite_data.py
.\.venv\Scripts\python.exe scripts\install_solar_model.py
```

Normal image analysis does not run these installers. The runtime dependency lock
was refreshed after adding ONNX Runtime, tokenizers and WebSocket support.

## APIs, persistence and telemetry

| Route | Behavior |
|---|---|
| `GET /api/v1/solar/status` | Local pack presence/coverage and model installation status |
| `POST /api/v1/images/{id}/solar-analysis` | `mode: closeup`, or `mode: field` with `solve_id` and `observation` |
| `GET` on the same image route | Latest saved solar result or JSON null |
| `WS /api/v1/telemetry` | Read-only versioned status snapshots and sequence numbers |

The `observation` object uses the existing site/time schema. `target_id` remains
part of that schema but does not supply the analysis answer. Field requests reject
unsolved or different-image WCS records. Solar results and their original evidence
levels are persisted in SQLite. Saved observation records include a solar-result
snapshot with its own analysis context; changing an observer setting later does
not rewrite that saved context.

The WebSocket currently emits `status.snapshot` once per second, including UTC,
sequence, image-only mode, camera not configured and **simulated** mount state.
It receives no device commands. More detailed frame/quality/solve event types in
the earlier architecture plan remain future work. Reconnection is manual via
reload; REST APIs remain available if the stream disconnects.

## Validation and remaining work

**56 tests passed** in the final full run. New checks cover:

- Local satellite prediction, missing date coverage, and no runtime Python network
  requests after the astronomy library's harmless import-time compatibility probe.
- WCS-based Ganymede association in an explicit synthetic geometry fixture, with
  an unrelated selected target (Vega), and rejection of another image's solve.
- Blank-image rejection, result persistence, and read-only WebSocket snapshots.
- Real local-model execution on the credited NASA Moon and Jupiter reference
  mosaics, returning tentative names while leaving plate-solve status unset.
- Uranus/Neptune target availability and position calculation.

The existing real ASTAP/Siril tests still pass. The test environment initially
stalled while creating a Windows loopback socket; the final run used normal local
socket access. This was not an astronomical solver failure.

The two NASA mosaics are **reference smoke tests**, not representative ground-based
camera observations or an accuracy study. Their provenance is retained in
`samples/solar/README.md`. The previous Altair star image returned **unknown** in
a direct close-up rejection check. No model was trained or calibrated against the
proposed PVOL-based collection. Independent Horizons comparisons, real telescope
moon-system images, glare/ring/occultation modeling and held-out recognition
statistics remain required. The proposed 300 independent images are not collected.

Core changes: `astrolearn/solar.py`, `static/solar.js`, the Solar System panel,
the telemetry route in `main.py`, saved observation snapshots, and installation
scripts. Earlier research/architecture documents describe their historical state;
this document is the current implementation record.
