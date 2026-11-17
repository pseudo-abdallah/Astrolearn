# Improve offline plate-solving success

Priority agreed November 4, 2026. INDIGO/Alpaca hardware integration is deferred
in [the offline-first plan](offline-first-plan.md#later-hardware-interoperability--added-november-4-2026).

## What the baseline actually proves

- Four independent DSS fields solve with genuine approximate pointing/scale
  hints. FITS and PNG variants are the same four observations.
- The complete software benchmark passes 11 checks, including those eight
  variants, one synthetic blind control and two negatives. This is not an
  11-image real-world success-rate measurement.
- Two difficult, low-resolution user star photos still fail blind searches.
  Their original field height/acquisition metadata has not been established.
- New uploads and reanalysis run fresh; no cached WCS or selected catalog target
  may count as successful image recognition.

Current bottleneck: solving unknown raster images without scale or pointing
hints. Improving named-star overlays alone does not fix that bottleneck.

## Work order

| Priority | Work | Evidence required before adopting a change |
| --- | --- | --- |
| 1 | Record native usable-star count, scale trials, selected catalog, timeout and elapsed time for each attempt. Distinguish timeout, poor extraction and catalog mismatch. | Reproduce each difficult image and explain which stage failed; OpenCV candidate count must not be presented as native solver star count. |
| 2 | Improve scale/pointing input: retain original metadata and use actual FITS calibration or user-provided field height. Evaluate missing intermediate scales and a longer explicit thorough-search mode. | Compare blind and hinted runs of identical pixels with reuse disabled and the same time budget. Never use the selected learning target as an image-position hint. |
| 3 | Preserve available 16-bit raster intensity and original metadata through upload and native FITS conversion. Current raster conversion uses 8-bit luminance. | Compare original high-bit-depth survey/camera data against the current conversion, including orientation and WCS overlays. Do not invent missing sensor/focal-length data. |
| 4 | Test gentle background flattening, alternative luminance channels and conservative star filtering on solver copies. Keep original pixels and processing provenance. | Measured recovery on failed real images, no loss on current positives, and no false solves on noise/blank controls. Avoid cosmetic sharpening or synthetic stars. |
| 5 | Extend crop recovery where it measurably helps. Validate the full-frame mapping, including regions outside the matched crop. | Check WCS coordinates across the frame against an independent reference. A center check alone does not establish full-frame accuracy. |
| 6 | Evaluate a dedicated blind-solver fallback, such as local Astrometry.net with suitable indexes, in a supported local environment. | Confirm Windows/WSL or future Pi/Linux installation requirements and index coverage before installation. Prove offline operation and measure resource use. |

The first scale experiment tests 1°, 4° and 0.5° on a previously failing uploaded
photo. These are search hypotheses; none is accepted as an image calibration.
Its raw outcome is saved in `plate-solving-scale-experiment.json`. Do not change
production defaults solely because one image succeeds or one trial times out.

Measured result: 1° and 0.5° exhausted their 20-second native budgets; the 4°
trial completed in about four seconds without a match. Its native log reported
503 stars, 424 quads, the D50 database, and a small-image-dimensions warning.
Therefore this photo is not failing simply because OpenCV found no sources.
No success-rate improvement is claimed from this experiment.

An instrumentation fix now retains ASTAP's partial native log on timeout,
before the isolated working folder is deleted. That makes future comparisons
include the actual catalog/extraction stage instead of only a timeout message.
The solver-metadata regression tests pass 4/4, including a timeout that writes
a native log and verifies that its contents survive cleanup. This is diagnostic
coverage, not evidence that the difficult image now solves.

ASTAP's documentation recommends image height within roughly 5%, explains that
its automatic narrow-scale search covers approximately 0.3–10°, and identifies
star quality, dynamic range, distortion and resolution as factors. Widely
spaced explicit trials therefore leave blind-search gaps. Increasing star-name
catalog size does not directly resolve these pattern-search failures.

## Measurement and acceptance

Build a local set of at least 30 independent real star-field images, with a
held-out subset that is not used for tuning. Include different field heights,
dense/sparse fields, saturation, gradients, noise, modest blur and optical
distortion. Retain original file provenance and independent reference WCS where
available. Crops, rotations and re-encodings remain variants of their parent
observation, not additional independent successes.

Report separately:

1. Hinted solving: actual approximate scale/pointing supplied.
2. Blind solving: no scale/pointing, no hidden header hints and no cached results.
3. Stress/challenge images: intentionally poor data or severe distortion.
4. Negative controls: blank, noise, ordinary photographs and starless close-ups.

For each positive record: fresh solve outcome, reference-coordinate error,
full-frame residual checks, time, peak resources, engine/catalog and processing
variant. Report timeout separately from a completed unsuccessful search.
Negative controls must not receive accepted WCS solutions. A Moon/planet
appearance suggestion is not an astrometric success.

Adopt improvements when held-out real-image recovery increases at a declared
fixed time budget, current validated positives remain correct, and negatives
remain rejected. Label success targets as goals until measured. Retain the
working baseline for comparison rather than repeatedly tuning to the same two
failed pictures.

## References

- [ASTAP solving checklist and command-line options](https://www.hnsky.org/astap.htm)
- [Existing fresh-pipeline results](../samples/plate-solving-test-set/results.json)
- [Current test-set instructions](../samples/plate-solving-test-set/README.md)
- [Earlier debugging and limitations](fresh-solving-debug.md)
