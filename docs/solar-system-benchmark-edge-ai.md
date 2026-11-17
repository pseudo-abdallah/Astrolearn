# Solar-system extension, camera benchmark and edge AI

**Implementation update:** the two Solar System image-analysis paths, date-bounded
Jupiter/Saturn satellite excerpts and read-only WebSocket telemetry are now
implemented. See [the current implementation and 56-test validation](solar-system.md).
The dataset collection and model-calibration proposals below remain future work.

Prepared November 3, 2026. Scope: the seven other Solar System planets, our Moon,
then the four Galilean moons and Titan where image resolution permits. The laptop
continues to stand in for the future Raspberry Pi; no camera or motor is assumed.

## Research conclusion

Keep three distinct data resources: **star catalogs** for solving the background,
**ephemerides** for predicting moving bodies, and **labeled camera images** for
testing image quality and close-up suggestions. Adding planet pictures to Gaia
does not extend Gaia into a moving-body solver. A large number of augmented
images also does not establish a high success rate on independent observations.

The supplied research excerpt supports a modular design, but references [21]–[28]
were supplied without their bibliography. Its numerical accuracy and speed claims
were not independently verified here and must not be reported as AstroLearn
results. Learned optical alignment also needs measured mechanical/optical errors
for our actual instrument; pictures alone cannot validate such a control model.

## Better test collection

**PVOL is the primary candidate.** Its authors describe an archive of amateur
planet observations, including the Moon and Galilean satellites. This is more
representative of Earth-based telescope output than spacecraft publicity images.
See the [PVOL authors' paper](https://arxiv.org/abs/1701.01977) and
[PVOL website](https://pvol2.ehu.eus/). The website timed out during this session;
no bulk image collection, image rights or download API has been verified.

**ALPO-Japan is a secondary reference, subject to permission.** It has a planetary
image archive, but its homepage explicitly requires staff permission for reuse of
images/material. It also discourages AI image processing that alters real
features. We did not download its images or treat them as a freely reusable ML
dataset. See the [archive and its notices](https://alpo-j.sakura.ne.jp/Contents/homeE.htm).

**Use calibrated star fields for the astrometry benchmark.** Existing NASA SkyView
DSS FITS data has reference WCS that can be withheld from the solver input and
used for independent coordinate checks. It does not test planetary close-up
recognition. Preserve each survey's provenance and rights information.
[SkyView documentation](https://skyview.gsfc.nasa.gov/current/docs/batchpage.html).

**Use a camera simulator for the acquisition workflow.** Sky Simulator documents
artificial imagery and ASCOM/Alpaca camera, mount and focuser workflows, including
solving simulated exposures. It is an optional future adapter, not something
installed or used by AstroLearn yet. Artificial catalogs can create circular
evaluation if they are also the solver's only reference.
[Simulator setup](https://sky-simulator.sourceforge.io/).

Start by curating **300 independent source images**, with the target allocation
in `benchmarks/source-registry.json`. Treat this as a collection goal, not an
inventory claim. Include varied observers, nights, image scales, phases, seeing,
filters, exposures and processing levels. Include empty skies, stars, blurred
disks, terrestrial round objects, diagrams and edited images as rejection cases.
Do not silently mix UV/IR planetary pictures with visible-light camera examples.
Keep original/raw or lightly processed frames distinct from sharpened stacks.

Require source URL, attribution/rights, target-label evidence, observation time
(or explicitly unknown), observer/session group, filter, camera/telescope metadata
when available, and processing history. Keep original labels out of filenames
used by recognition, and mask/crop embedded target-name text without inventing
image detail. All frames from one video/session and all derivatives of one image
stay in the same train/validation/test split. Hold out observers/nights as well as
images. Never tune thresholds against the final test set.

## Camera-like collection implemented now

`astrolearn/camera_benchmark.py` and `scripts/make_camera_collection.py` create
eight reproducible variants of a local licensed source: nominal, low signal,
defocus, bright background, saturation, tracking trail/shift, hot pixels and a
combined case. The noise model uses relative Poisson photoelectron counts,
Gaussian read noise, a gain, bias and a 12-bit clipping limit. These parameters
are illustrative, **not specifications for a confirmed camera**. They do not
model a measured atmospheric PSF, Bayer processing, atmospheric dispersion,
real detector defects, diffraction, guiding errors over time or full optics.

The generator writes solver-input FITS files **without celestial WCS hints**.
Reference headers are stored separately; translation adjusts reference CRPIX.
Frame checksums, random seeds, profiles and parent/session groups are recorded in
a manifest. Inputs are preserved. No AI enhancement modifies scientific truth.

```powershell
.\.venv\Scripts\python.exe scripts\make_camera_collection.py samples\altair-dss2-red-1deg.fits --source-url https://skyview.gsfc.nasa.gov/ --group dss-altair-reference --output data\benchmarks\dss-altair
```

This command was run: **eight derived FITS frames from one independent DSS
reference** exist under `data/benchmarks/dss-altair/`, with manifest
`manifest-96db32f26409.json`. Two new tests passed for reproducibility, input
preservation, detector bounds, separate truth and shifted reference coordinates.
The eight frames have **not yet been run through a solve-success benchmark**.
They are a reproducible start, not the proposed 300-image collection.

Use the same generator with legally reusable planetary telescope frames once
curated. A close-up without reference WCS stays without reference WCS: its test
truth is the documented target identity or measured disk/mapping annotations,
not invented sky coordinates.

## Strengthen the Solar System catalog

`resources/solar-system-extension.json` defines the initial target IDs, NAIF
body identifiers, required packs and evidence rules. It is a **resource plan**;
it is not loaded into the active target selector and does not assert installed
satellite support.

The existing DE421 resource supports the planets/system barycenters and Earth's
Moon. Io, Europa, Ganymede and Callisto need an appropriate Jupiter satellite
kernel; Titan needs a Saturn satellite kernel. JPL lists JUP365 and SAT441L,
with documented coverage. Select a practical date interval and pack size before
installing them; do not download full multi-century packs on an inference request.
Use the [JPL satellite-file table](https://ssd.jpl.nasa.gov/sats/ephem/files.html)
and [NAIF kernels](https://naif.jpl.nasa.gov/naif/data_generic.html).

Do not confuse a planetary system's barycenter with the planet's physical center.
Validate loaded kernel center/target chains, date coverage, observer location,
light-time and reference-frame conventions before projecting moon positions into
WCS. Retain version, source and hashes. Missing/out-of-range resources must report
unsupported, not silently fall back to a guessed moon name.

For moon labels, prioritize **parent-system geometry**, not texture classification:
solve the background when possible, compute the parent and moon directions at
the actual observation time/site, measure candidate image positions and compare
the pattern. Tiny Io/Europa dots cannot reliably be named by appearance alone.
Blend, glare, eclipse, occultation, overlap and inadequate angular resolution must
allow an unresolved or ambiguous result. The ability to predict a moon's position
does not establish that this telescope can detect it.

## Application architecture

| Layer | Responsibility | Current state / next step |
|---|---|---|
| Application service | FastAPI REST; typed jobs; observation records; WebSocket status events | REST exists; WebSocket telemetry is planned, not implemented |
| Acquisition | Uploaded-image/replay provider now, future camera provider behind one interface | Uploads work; camera generator produces replay fixtures; no real camera configured |
| Astronomy | Astropy + Skyfield with local versioned JPL data | DE421 exists; satellite-kernel extension pending |
| Imaging | OpenCV source/disk candidates, quality metrics, immutable originals | Existing metrics are deterministic, not a trained quality model |
| Astrometry | ASTAP/Siril → actual FITS WCS | Existing offline engines; do not count close-up classification as a solve |
| Moving-object association | Ephemeris + WCS + actual time/site + measured candidates | Early backend code exists; full moon-system support and validation pending |
| Edge AI | Quality classification, candidate ranking, conservative close-up suggestions | Experimental local CLIP/ONNX backend/resources exist; no validated planetary test accuracy or Pi benchmark |
| Education | Explanations from local catalog and the actual evidence/result | Local catalog works; optional cached enrichment remains separate |

Proposed telemetry events are `frame.ready`, `quality.updated`, `solve.progress`,
`solve.completed`, `recognition.completed`, `resource.warning`, with a schema
version, sequence number, UTC, job/image ID and evidence level. Keep telemetry
read-only; simulated motor status must never imply physical motor telemetry.

## Edge-AI recommendation

Begin with **image-quality triage**: too blurred, too dim, saturated, trailing,
or usable. Compare a small ONNX quality model against existing deterministic
OpenCV metrics before adopting it. A second small disk/candidate model can rank
possible Moon/planet close-ups and explicitly reject unknown inputs. Retain
originals and never use AI-generated surface detail as identification evidence.

The downloaded generic CLIP model is a baseline experiment, not a validated
astronomy model. Its similarity thresholds are currently uncalibrated. It has
not established accuracy on real telescope planets/moons, and its roughly
154-MB graph is not automatically the best edge choice. Benchmark a smaller
task-specific model after a legally usable dataset is curated. ONNX Runtime has
[official edge/Raspberry Pi deployment guidance](https://onnxruntime.ai/docs/tutorials/iot-edge/),
but laptop performance does not establish Pi latency, memory or temperature.
No accelerator/HAT/GPU is assumed. Core astrometry must work without an LLM.

Record balanced accuracy/F1, confusion matrix, unknown rejection and false
identifications, along with p50/p95 warm latency, cold-load time, peak memory and
model size. For WCS, report solve rate by difficulty, timeouts and independent
coordinate residuals. For moons, report angular/pixel association errors and
ambiguous cases, not only successful examples. Evaluate the Pi when available.

## Recommended implementation order

1. Curate licensed telescope seeds and record metadata/independent groups.
2. Expand the benchmark with the camera generator and real unmodified hold-outs.
3. Add/test date-bounded Jupiter/Saturn moon ephemeris packs and true body centers.
4. Complete UI and evidence handling for field association and tentative close-ups.
5. Train/calibrate a small quality model and compare it with the baseline.
6. Add replay/telemetry integration, then test a native Pi deployment later.

This work did not install satellite kernels, train a new model, collect 300 real
images, implement WebSockets or complete the unfinished close-up UI. It adds
researched sources, an explicit resource plan and a tested local benchmark tool.
