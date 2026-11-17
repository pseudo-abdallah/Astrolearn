# AstroLearn offline-first development plan

Agreed November 2, 2026. The application must complete its core workflow without
internet access. Connectivity can improve results through optional services, but
must never be required to start, identify a field, learn, or save an observation.
The current prototype uses uploaded pictures; camera and mount hardware are later
adapters. Laptop motor controls remain explicitly simulated.

## Offline core and optional enhancements

| Feature | Required offline behavior | Optional online improvement |
|---|---|---|
| Images | Upload PNG/JPEG/TIFF/FITS; detect sources; assess relative sharpness | Download reference images |
| Plate solving | Local ASTAP with installed star databases and bounded jobs | Explicit cloud fallback after local failure |
| Identification | Match detected sources to a locally installed catalog using the solved WCS | Retrieve additional facts or expanded catalogs |
| Charts | Local reference charts and constellation data | Explicit catalog/resource updates |
| Astronomy | Local target catalog, Astropy/Skyfield and planetary ephemeris | Optional independent ephemeris cross-check |
| Education | Stored facts and explanations | Extra articles or clearly labeled optional AI explanations |
| History | Local images, results, notes, metadata and export | Optional user-requested backup |
| Hardware | Local device adapters; simulation until devices exist | No internet dependency |

## Architecture

### Later hardware interoperability — added November 4, 2026

Defer INDIGO and ASCOM Alpaca integration until the image-solving baseline is
stronger and the actual camera/mount are confirmed. Retain the local simulator
as the current adapter.

- [INDIGO](https://github.com/indigo-astronomy/indigo): evaluate its device bus,
  camera/mount simulators and supported Raspberry Pi/Linux drivers through an
  optional AstroLearn adapter.
- [Alpaca Benro Polaris](https://github.com/ogecko/alpaca-benro-polaris): study its
  telescope API, alignment and tracking workflow. Its Polaris-specific driver
  is not assumed compatible with AstroLearn's future hardware.
- Define adapter operations for GoTo, stop, position, tracking and sync. Later
  test a feedback loop: target -> simulated motion -> image -> verified solve ->
  pointing error -> simulated correction. Real calibration and motor conversion
  require confirmed hardware and measured behavior.

These are later tasks; current priority is measurable offline plate-solving
success. See [the success-rate improvement plan](plate-solving-success-plan.md).

The local interface communicates with the local Python backend. The backend owns
astronomy calculations, image processing, offline solving, identification, local
catalogs, educational content, persistence and the mount adapter. Online adapters
are separate optional providers. Their errors cannot invalidate a working local
result or block a local observation.

## Identification milestone

1. Retain the complete WCS from a successful ASTAP solve, not just its center.
2. Install a versioned local star/name catalog and a local deep-sky object catalog.
3. Project catalog sky coordinates onto the exact uploaded-image preview.
4. Match compact source detections to catalog stars with distance and ambiguity
   checks, independent of the target selected by the user.
5. Label reciprocal, unambiguous matches as **matched detections**. Label catalog
   objects whose locations fall in the field without detection evidence as
   **expected objects**. Leave other detections unidentified.
6. Let the user inspect names, identifiers, coordinates and matching status.
7. Persist WCS, catalog provenance and identification results with the solve and
   saved observation; restore them when reopening the image or observation.

No successful solve means no inferred identities. A catalog object inside a frame
does not prove that the object is visible. Deep-sky extended-object detection is
separate from star centroid matching. Planet identification needs observation-time
ephemerides and is not supplied by a static star catalog.

## Local resources

Install solver binaries, matching star databases, catalog coordinates and names,
deep-sky records, planetary ephemeris and educational content before offline use.
Use celestial_data's suitable datasets with attribution and license copies. Check
formats, coordinate conventions, units and source provenance on import. Record
revision, checksums and counts. Astropy WCS handles pixel/sky transformations.
Starplot reference charts and constellation overlays are later additions.

Startup reports missing resources with a specific message. Runtime must not
download dependencies, catalogs, ephemerides, fonts or solver indexes silently.
Fresh installation and explicit resource updates may require internet access;
normal use after setup must not.

## Online policy

- Wi-Fi association is not proof of usable internet. Check an optional service
  only when requested, with a short timeout.
- Prefer local results immediately. Preserve them when an optional request fails.
- Never upload images automatically. Request explicit user action for cloud solves.
- Cache suitable additional information with its source and retrieval time.
- Stage resource updates separately, validate them, and retain the working version.
- Offline educational answers use stored facts. Local conversational AI requires
  separate performance and accuracy evaluation; it is not a prerequisite.

## Delivery stages and completion criteria

| Stage | Deliverable | Completion evidence |
|---|---|---|
| 1 | Resource import, versions and attribution | Known catalog entries and checksums verified |
| 2 | WCS, star matching, labels and details | Deterministic geometry tests plus real ASTAP integration |
| 3 | Reference charts, constellation overlays and richer local learning | Local rendering and interaction checks |
| 4 | Complete labeled-observation persistence | Save, restart, reopen and export checks |
| 5 | Optional internet adapters | Offline results survive timeout/disconnection; no implicit image uploads |
| 6 | Real device adapters | Bench and field measurements on confirmed hardware |

## Offline acceptance tests

Block external networking without changing the user's computer network settings.
Verify startup, every main screen, upload, real plate solving, identification,
astronomy, educational facts, saving, restart and reopening records. Verify
unsuitable pictures, no solution, ambiguous matches and missing resources remain
honest failure/unknown states. Synthetic integration images verify plumbing;
independent real astronomical photographs are needed to measure identification
accuracy. Physical tracking, GPS and independent E-stop require real equipment.

## Implementation progress

Implementation progress: the versioned identification pack, full-WCS retention,
unique star matching, interactive labels, expected-object distinction, and saved
label restoration are now implemented. The identification milestone passed 33
automated tests including real local solver integration. Charts, constellation
overlays, richer educational content, online adapters and real hardware remain
later work; this milestone does not declare the entire roadmap complete.

## Sources

- https://github.com/dieghernan/celestial_data
- https://github.com/steveberardi/starplot
- https://docs.astropy.org/en/stable/wcs/wcsapi.html
- https://www.hnsky.org/astap.htm
# Implementation update — November 2, 2026

Siril with a verified local Gaia catalog is integrated alongside ASTAP. The
previously failing Altair image now solves and receives a positional Altair
label. Local sky exploration, persistent brightness CSV lessons, and explicit
SIMBAD enrichment with an offline cache are also available. See
[the integration guide](integrations.md) for working steps, exact feature scope,
resource provenance and the 46-test validation results. Other external tools
remain optional references as documented there.

