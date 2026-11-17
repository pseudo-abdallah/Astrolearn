# Astronomy resources for AstroLearn

Reviewed November 2, 2026. This is an integration assessment, not a claim that
these services are installed or that the unresolved Altair photograph is solved.

**Implementation update:** Siril/local Gaia, the local sky map, cached SIMBAD
details and the brightness viewer are now implemented. Altair now solves and is
labeled. The assessment below records the earlier planning state; see
[the integration guide](integrations.md) for current scope and validation.

## Priority: reliable offline image identification

The image workflow remains: original pixels → source extraction → verified
celestial image mapping (WCS) → local catalog projection → conservative source
matching → names and learning information. A selected target, source webpage,
or FITS header alone does not verify an identity.

1. Evaluate an alternative local solver against the exact failing image and a
   representative set of ordinary telescope photographs. Siril documents a local
   Gaia DR3 astrometric catalog and a local Astrometry.net backend. Its internal
   solver normally needs approximate position and scale; local Astrometry.net
   supports blind position/resolution options. Neither guarantees this thumbnail
   can be solved. Download required catalogs/indexes during setup, not per image.
2. Preserve the existing ASTAP backend as a measured baseline. A second backend
   must return actual pixel-derived WCS and diagnostics through the same job API.
3. Validate full-image coordinates and parity before applying labels. Siril may
   flip an image by default; an adapter must preserve preview alignment (e.g.
   use its documented `-noflip` behavior and verify WCS against the original).
4. Add online metadata enrichment only after coordinates are verified. Cache
   useful records locally with source and retrieval date. Network availability
   must not be required for existing local identification or observation history.

Source: [Siril plate-solving documentation](https://siril.readthedocs.io/en/stable/astrometry/platesolving.html).

## What each resource contributes

| Resource | Useful role | Offline decision |
|---|---|---|
| [Siril](https://siril.org/) | Alternative plate solving, calibration, registration and stacking | Evaluate a local backend and catalog; not yet integrated |
| [GraXpert](https://graxpert.com/) | Background-gradient processing | Optional later; preserve originals and test any effect on astrometry; not a solver |
| [SIMBAD](https://simbad.unistra.fr/simbad/) | Names, identifiers, object types and published measurements | Optional online enrichment with bounded local caching; not an image matcher |
| [Cosmoscope](https://cosmoscope.space/) | 3D exploration and object information design | Learn interaction ideas; do not make the offline UI depend on a hosted page |
| [AstroViewer](https://astroviewer.net/av/en/index.php) | Sky display controlled by location and time, constellation/name toggles | Implement a local map from bundled catalog/ephemeris; hosted widget is optional |
| [Lightkurve tutorials](https://lightkurve.github.io/lightkurve/tutorials/index.html) | Brightness time series, photometry and transit analysis | Later educational module using predownloaded example files |
| [MAST / TESS](https://archive.stsci.edu/missions-and-data/tess) | Scientific pixel files, light curves and archive tutorials | Download selected teaching datasets once, retain provenance locally |
| [exo.MAST](https://exo.mast.stsci.edu/) | Known exoplanet parameters and related archive data | Optional enrichment/education; a single ordinary photograph does not establish a transit |
| [Spartificial projects](https://github.com/Spartificial/yt-acad-projs) | Educational ML notebooks, including exoplanets and classification | Teaching reference; inspect each notebook's data assumptions and reuse terms first |
| [Joey Troy article](https://joeytroy.com/how-ai-helped-me-choose-the-best-telescope/) | Example of organizing telescope selection criteria | Context for later equipment decisions, not an image-solving component |

The submitted Lightkurve and TESS tutorial URLs were incomplete or inaccessible;
the official tutorial index and MAST TESS documentation above are usable starting
points. No third-party source code or hosted interface was imported in this review.
Check actual code/data licenses and attribution requirements before redistributing
any resource; a public website alone does not establish permission to copy it.

## Current verified status

The updated prototype reads calibrated FITS metadata as unverified search hints,
pins ASTAP extraction defaults and preserves native logs on new failed jobs.
The full suite passed **37 tests**, including real local ASTAP fixture checks.
The latest Altair attempt failed and its diagnostic-log endpoint returned HTTP
200. No successful Altair identification is claimed. The app remains running at
http://127.0.0.1:8000/.
