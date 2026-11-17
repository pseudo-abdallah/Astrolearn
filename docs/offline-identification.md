# Offline identification and labeling

## Using labels

Open `http://127.0.0.1:8000/`, upload an image and solve it locally. **Star names**
shows named matches; **Expected objects** shows catalog locations without confirmed
detections. Click a marker/label or search in **What's in this image?** to inspect
names, catalog identifiers, coordinates, magnitude and matching evidence. The
chosen observing target never supplies image identities.

For `samples/synthetic-orion-wide.png`, use field height 40 degrees and radius 180.
New solves save their full image mapping and identification results. Older solves
need to be run again. The image library restores the latest job; history restores
that observation's exact solve. Saved observations and JSON exports retain labels.

## Local catalog and provenance

The installed pack has 41,411 stars, 541 with names, and 110 Messier objects. It was
imported from celestial_data revision `44e2cf2c1290c41e9d93dc899ce6a784e011349b`.
Source attribution and the unchanged BSD-3-Clause license are retained under
`astrolearn/data/identification/`, along with `catalog.json` and `manifest.json`.
The manifest records the revision, source/output checksums, counts and frame.

Application startup and identification read only these local files. The explicit
setup command `python scripts/import_identification_catalog.py` downloads the data;
the running app never calls it. The importer joins star names by HIP identifier and
normalizes longitude-like catalog angles to RA in [0, 360) degrees. Source datasets
include the XHIP star compilation, name cross indexes and Messier/SEDS records.

## Coordinate and matching method

ASTAP writes a FITS-standard `.wcs` header. The actual header, including projection,
CD matrix, reference pixel and any distortion terms, is retained before its
temporary directory is removed. It is not reconstructed from only center and
rotation. Width and height are attached to ASTAP's header-only result.

Raster images are converted to a temporary primary FITS array before solving,
avoiding PNG/JPEG versus FITS vertical-convention ambiguity. A preview's column x
and row y correspond to zero-based WCS pixels without a further y flip. Original
FITS arrays remain unchanged. Astropy projects catalog coordinates into the preview;
out-of-frame, non-finite and non-convergent projections are excluded.

A match requires exactly one detected source within 3 pixels of a projected star,
and exactly one catalog star within that source's 3-pixel radius. Blends and
multiple possible matches stay unidentified. Pixel residuals and angular separation
are displayed; confidence percentages are not invented.

| Evidence | Meaning |
|---|---|
| Matched star | Unique positional source/catalog coincidence using a successful plate solution |
| Expected star | Named catalog location in the frame without an acceptable detection match |
| Expected Messier object | Catalog location in the frame; extended-object detection has not confirmed it |
| Unidentified source | Compact bright candidate without an accepted unique catalog match |
| Identification unavailable | Missing/corrupt catalog, invalid/missing WCS, or an older solve |

Named and bright stars get priority. Responses retain at most 300 matched-star
details and explicitly report the total/truncation. The list displays up to 80
filtered entries; search covers all retained records. Canvas labels avoid overlap.
Clicking a marker can inspect retained stars without permanently drawn labels.

## Limits

These are positional matches, not spectroscopic verification. Catalog coordinates
are static J2000 without observation-epoch proper-motion correction. The selected
star dataset reaches roughly magnitude 8, so faint stars in narrow telescope fields
may be absent. Most stars have identifiers, not common names. A Messier identifier
such as M42 is a valid object label even without a common-name alias. Planets and
satellites need time-dependent matching. Nebula/galaxy detection, constellation
overlays, reference charts and richer local learning content are later stages.

## APIs and validation

- Solve jobs contain `solution.wcs_header` and an `identification` result.
- `GET /api/v1/images/{image_id}/latest-solve` restores an image's latest solve.
- `GET /api/v1/solves/{solve_id}/wcs` downloads the image mapping as text.
- Sessions retain the identification snapshot and solve ID.
- `GET /api/v1/prototype/status` reports local catalog readiness.

Tests cover rotated WCS and RA wrap, preview orientation, ambiguous matches,
expected/detected distinctions, invalid resources, real PNG and mirrored FITS
ASTAP solves, target-independent names, and saved labels after restart. Python
network calls are blocked during the real identification integration tests. This
does not claim OS-level firewall verification of the native ASTAP process.

The synthetic Orion PNG produced 1,140 unique matches, including 30 named stars
such as Betelgeuse, Rigel and Bellatrix. A mirrored FITS solve can reject some edge
stars because its fitted WCS differs slightly; tests do not loosen the radius to
force those identities. These are synthetic integration results. Identification
accuracy on independent real astronomical photographs remains to be measured.

## References

- https://github.com/dieghernan/celestial_data
- https://docs.astropy.org/en/stable/wcs/wcsapi.html
- https://www.hnsky.org/astap.htm
## Galaxy names in narrow solved fields

The offline OpenNGC supplement adds 11,994 extended objects. It is stored
separately from the bright-star/Messier catalog and credited to Mattia Verga
and the OpenNGC contributors under CC BY-SA 4.0. The companion manifest records
the source revision, conversion and checksums, and the license is bundled with
the data. Regenerate with `scripts/import_openngc.py CSV REVISION`.

AstroLearn projects their catalog centers into the solved frame. Their names
appear as catalog objects in the field, separate from individually matched
stars. On reopening an older analysis, AstroLearn updates the labels from its
saved WCS without running another solve. The uploaded Antennae frame was
checked against its saved WCS and both NGC 4038 and NGC 4039 fall inside it.

- [OpenNGC catalog](https://github.com/mattiaverga/OpenNGC)
- [NASA: Antennae Galaxies](https://science.nasa.gov/mission/hubble/science/explore-the-night-sky/hubble-caldwell-catalog/caldwell-60-61/)

