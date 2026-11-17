# Troubleshooting an unsolved photograph

**Update:** the Altair case below is now resolved with the integrated Siril/local
Gaia backend and saturated-core source measurement. The historical ASTAP failures
are retained as investigation evidence. See [the working settings and validation](integrations.md).

## What the result means

Green OpenCV circles are compact bright candidates, not a successful sky-pattern
match. ASTAP extracts its own stars using different filtering and signal-to-noise
thresholds. A large candidate count does not guarantee a solve. The program must
continue to show unverified pointing when no solution exists.

## Start with the image source

Prefer the original full-resolution image or FITS rather than a webpage thumbnail,
screenshot or heavily edited crop. The field of view is the angular image height
in degrees, not its pixel dimensions. For example, 30 arcminutes is 0.5 degrees.
Do not reuse the synthetic demo's 40-degree field setting for an unrelated photo.

If the source identifies a target, choose that target and use **Optional pointing
hints → Use selected target as search hint**. This fills RA/DEC and a 5-degree
search radius. A hint only narrows a search; it is not evidence of identification.
Enter the actual field height when available; otherwise the solver's automatic
scale search is limited. Very narrow or wide fields may need an explicit value.

## Match the local database to the image

ASTAP's approximate recommended image-height ranges are:

| Database | Image height |
|---|---|
| D80 | 0.15–6 degrees |
| D50 | 0.2–6 degrees |
| D20 | 0.3–6 degrees |
| D05 | 0.6–6 degrees |
| G05 | 3–20 degrees |
| W08 | 20–80 degrees |

The interface reports installed coverage. These are usability guidelines, not
guarantees. A large bright-star halo, saturation, small resolution, insufficient
background stars, distortion or image processing may still prevent a match.
Enlarging a thumbnail does not recreate missing detail.

For an image smaller than roughly 1280 × 960, the original higher-resolution file
is preferable, although smaller images can work. ASTAP recommends roughly 30 or
more usable stars and sharp, reasonably round star profiles. See the author's
current solving checklist: https://www.hnsky.org/astap.htm#conditions

## Altair investigation on November 2 2026

The user's 512 × 511 image produced 331 OpenCV candidates. A separate local ASTAP
extraction at SNR 10 exported 34 sources. Automatic field-height / 180-degree
search attempts failed, and an Altair-hinted 5-degree search also failed with the
original installed catalogs (D05, G05, W08). This establishes failure, not the
identity of the star. The user supplied this source page:
https://www.star-facts.com/altair/altair-nasa-2/

The source's Altair identification can be used as a hypothesis for a search
around RA 297.6958 degrees, DEC +8.8683 degrees. Only a real solved background
pattern can verify the image. D50 was subsequently installed locally and the
resource manifest regenerated (3,245 solver/catalog/ephemeris files). The image
still failed an Altair-hinted automatic search and trial field heights 0.25 and
0.15 degrees. The latter were diagnostic trial scales, not measured field sizes.
The source page's 700 × 665 WebP also failed the automatic hinted search.

The detailed ASTAP log reported small image dimensions. For the 0.15-degree
trial it selected 113 stars and 88 quads with D50 but found no matching solution.
The automatic log searched approximate field heights 9.5 down to 0.37 degrees.
These failures do not establish a single cause or prove the photo impossible to
solve with other techniques. The next reliable input is the original scientific
FITS image or a known angular image height / pixel scale. The application retains
unverified status rather than assigning the source page's identity as a result.

The interface was improved to show small-image, field-size, coordinate-hint and
catalog-coverage advice for new attempts. A selected-target hint button avoids
manual RA/DEC entry. The expanded regression suite passed 34 tests, including
failure-advice checks. No user image was sent to a cloud solver.

## Follow-up: calibrated input and native diagnostics

The unresolved Altair failure was reproduced outside the web application using
the official ASTAP CLI 2026.10.30. A prior CLI 2025 release also rejected a
separately downloaded, calibrated DSS survey field near Altair; this does not
establish a version regression. The survey contains strong saturation and a
large bright-star halo, but no single cause has been proved. Neither the survey
header nor the source webpage is counted as a successful pixel-pattern solve.
Temporary experiments are retained under `tmp/diagnostics/altair-survey` and are
not distributed as working examples.

FITS uploads now expose their celestial WCS position and angular height as
**unverified search hints**. Explicit user hints take precedence. This removes
manual entry for calibrated files while requiring ASTAP to verify the pixels.
Raster photos do not acquire guessed calibration.

New native failures retain a bounded local diagnostic log. Download it from the
failure panel or `GET /api/v1/solves/{solve_id}/log`. Historical attempts made
before this change have no saved native log. Solver extraction defaults are
explicitly set per call to avoid dependence on interactive GUI settings.

The Minor Planet Center data services provide minor-planet orbit/observation
information, not a replacement star-pattern solver:
https://data.minorplanetcenter.net/
They were not added as a dependency of the offline identification workflow.

Validation: the final full regression run passed all 37 tests, including real
local solver fixture checks and the added metadata/log persistence checks.
The user Altair photograph remains
unsolved. A more robust alternative offline solver remains necessary to evaluate;
this change must not be described as fixing that photograph.
