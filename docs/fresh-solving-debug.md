# Fresh-solving debug — November 3, 2026

## Problems reproduced

The browser had a stale page without the Sources control and a failed-fetch
notice. The source overlay worked after reloading, but the UI did not make
candidate counts or the distinction from identification clear. Asset URLs now
carry a new version and local HTML/static responses require cache revalidation.

The previous default could recover a saved WCS for identical uploads. That is a
valid convenience, but it masked whether a new solve worked. **New uploads and
Analyze again now always run fresh**, with `reuse_solution: false`. API reuse is
still available only by explicit opt-in. Opening a historical result is labeled
**saved result**; native reanalysis is labeled **fresh solve**.

Dense images were truncated in scan order, losing bright candidates near the
bottom of the frame. Candidates are now ranked by measured strength before the
2,000-source processing limit. Saturated photographic cores larger than 10,000
pixels were also discarded. Their limited inclusion now allows the fresh Vega
survey test to receive a positional match. Compact sources retain the 3-pixel
match limit; very large saturated cores allow 6 pixels, with residuals and the
actual radius reported. Blends and ambiguous matches remain excluded.

## Solver changes

- Unknown scale: bounded ASTAP trials at 2, 8, 40, 20, 70 degrees and its own
  automatic range, sharing a two-minute native-process budget.
- A bright-region heuristic also checks stars outside the region. Star fields
  and nebulae are not treated as planets merely because they contain a bright
  area. An uncertain close-up with enough candidates still gets a star solve.
- With genuine scale/position hints, a failed whole-frame solve can retry corner
  stars. The resulting WCS is translated into original image coordinates,
  including SIP distortion origins. A visible warning marks extrapolation.
- Expected deep-sky catalog locations appear in the result list with their
  evidence label. They are not promoted to detected objects.
- Sources toggle independently of Names. The displayed subset and full retained
  candidate count are stated explicitly, including the small-screen display cap.

## Verification

The final regression suite passes **66 tests**.

The independent test set is in
[samples/plate-solving-test-set](../samples/plate-solving-test-set/README.md).
The native pipeline passed 11/11 benchmark checks in a fresh temporary database:
four independent DSS fields in FITS/PNG variants, a blind synthetic wide-field
control, and blank/noise negatives. No previous WCS records were reused.

Vega and nine Pleiades proper names were matched. Andromeda's M31/M32/M110 and
Orion's M42/M43 are expected catalog locations. Orion required a corner-star
solve and its center error was about 9 arcseconds, so it is not equivalent to
full-frame astrometric validation.

Two recent user-uploaded star photos (`ee0a4eb9…` and `7fd8a8b5…`) still timed
out in fresh, blind scale searches. No names or successes were manufactured for
them. Their original field height or acquisition metadata would allow a more
focused test; the new pack establishes the working baseline without them.

Browser verification also uploads Pleiades through the normal UI, obtains
**Star field solved · fresh solve**, and checks source markers with Names off.
