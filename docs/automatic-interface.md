# Automatic interface — November 3, 2026

**Latest update:** [fresh-solving debug report](fresh-solving-debug.md).
New uploads now default to **fresh solving**, with result reuse disabled; the
reuse behavior described in the earlier regression notes below is API opt-in.
The UI labels restored results as saved and displays source counts explicitly.

The app now uses a plain two-column page with **Observe** and **Sky & learning**.
The System architecture and Saved observations tabs, workflow banner, separate
Solar System controls and manual step-entry panel were removed from the UI.
Existing records and legacy backend endpoints were retained.

## Image-routing regression fix

The first merged workflow could mistake connected bright horizons and white
photo borders for resolved Solar System disks. This bypassed plate solving on
star fields. Disk candidates now must be isolated from the image edge and fill
at least 20% of their bounding rectangle. Isolated ringed planets still qualify.

Successful WCS records are recovered even after a failed retry. Re-uploaded
copies can recover a previous solution only when their normalized original file
bytes match exactly (SHA-256), with provenance recorded in `reused_from_solve_id`.
Different crops or similar-looking pictures cannot inherit a WCS this way.
The duplicate upload gets its own solve record and fresh source associations.

Older automatic analyses are rechecked when selected. The interface distinguishes
**Star field not solved**, **Object uncertain**, and **Visual suggestion**, and
retains the actual solver failure instead of displaying the same generic message
for every case.

The affected Canopus re-upload recovered its real ASTAP mapping and named-star
association. Three landscape photos remained unsolved after routing was fixed;
additional 20- and 70-degree scale trials also failed. The 550 × 241 photo
reported too few usable stars in those trials. Routing repair does not guarantee
a valid WCS for arbitrary low-resolution or distorted landscape images.
See [the actual upload recheck records](routing-recheck-results.json).

Regression coverage includes borders/horizons, isolated elongated disks,
byte-identical re-uploads, intervening failed retries, and rejection of different
image bytes. The final full suite passes 62 tests.

## Image workflow

Adding/dropping a photo starts one automatic analysis. Selecting an earlier image
restores its latest analysis or starts one if it has none. A background job chooses
between resolved close-up recognition and star-field solving. A calibrated FITS
image takes the stellar-solver path; its header remains only a search hint.
Successful earlier stellar solutions for the same image can be reused. A failed
stellar match may fall back to a visual suggestion. Neither a suggestion nor an
unknown result creates a successful WCS record.

Results appear together under **Image analysis**. The same canvas displays star,
moving-body and tentative visual labels. **Image settings** contains optional
solver hints, capture time and detailed diagnostics. New images reset their
settings so an unrelated photo cannot inherit another image's search scale.
**Analyze again** runs a fresh attempt instead of reusing a previous solve.

Moving-body associations run automatically after a successful star solve **when
an actual capture time has been entered**. The observer's current clock is not
silently treated as a downloaded image's exposure time. With no capture time, the
star solution is still shown and a short note explains the optional setting.
Unknown angular scale, poor quality and missing resources can still prevent a
solution; automatic routing is not a guarantee of identification for any photo.

The resolved-object routing is a heuristic. The close-up model remains a generic,
uncalibrated appearance model, and tentative labels retain the “Possible” wording.
Selecting a catalog target does not supply an image's identity or automatically
alter its astrometric hints.

## Target and simulator workflow

Selecting a catalog entry immediately calculates its position for the current
time and observer location, then submits those coordinates to the simulator.
Changing observer location also recalculates after a short input debounce.
The simulator animates between coordinate positions over three seconds, with
live status delivered by the existing WebSocket. It records RA/DEC and altitude/
azimuth directly; it does not invent steps-per-degree calibration for real axes.
Targets below the horizon remain valid simulation destinations and are labeled
as below the horizon in the position display.

**Stop** freezes simulated motion and remains latched. **Resume** resets that
latch and sends the currently selected target. While stopped, target coordinates
can still be displayed but a selection cannot move the simulator. Sequence numbers
prevent an older result from replacing a newer command from the same browser.
This remains a coordinate simulation, not physical mount control or tracking.

## API additions

- `POST /api/v1/images/{id}/analyze`: queues the combined workflow. Optional
  `options`, actual `observation`, and `reuse_solution` fields.
- `GET /api/v1/analyses/{id}`: combined job status and results.
- `GET /api/v1/images/{id}/latest-analysis`: latest combined record.
- `POST /api/v1/mount/goto`: site/time/target plus browser `client_id` and monotonic
  `sequence`; returns calculated position and simulator status.

Combined jobs share the existing single native-solver executor and lock, persist
their results, and are marked failed if interrupted by a server restart. Existing
manual solver, Solar System, image, observation and simulator APIs remain usable.
The Siril adapter now maps the shared 180-degree default into Siril's supported
30-degree near-search limit and records the actual limit; ASTAP retains blind
search capability.

## Verification

The full suite passed **60 tests**, including a real Siril solve through the new
automatic path, cached-result reuse, a real local-model Moon close-up, persistence,
stale target command rejection, stop/resume and coordinate simulation completion.
The browser verified automatic analysis after adding a Moon reference image and
an immediate Vega target calculation/dispatch. Scientific evidence distinctions
and hardware limits from the Solar System guide still apply.

Code: `automatic.py`, `mount.py`, `prototype_store.py`, the simplified `index.html`,
`app.js`, and `normal.css`. No new runtime dependencies were required.
