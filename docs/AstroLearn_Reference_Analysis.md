# AstroLearn — reference analysis and implementation map

Reference numbers follow the 16 images in the request, from top to bottom. Composite images are treated as one reference, with each visible state examined. Analysis is based on the supplied pixels, not the underlying products or their documentation. Exact font families, pixel measurements, opacity values, transitions, animation, haptics, and hover behavior cannot be established from screenshots. Interactions below are either visibly demonstrated by paired states or explicitly proposed adaptations.

## Shared design direction

Keep AstroLearn's cosmic black (#070B14), midnight panels (#101A2D), cyan (#27D3FF), and violet (#8B5CFF). Cyan identifies selection, coordinates, and framing; violet identifies education and contextual guidance. Reserve amber for caution and red for stopping or faults. Use readable system sans-serif text with monospaced scientific values. Maintain an 8-point spacing rhythm, 16–24 px panel padding, 12 px control corners, and 18–22 px panel corners. These are AstroLearn design decisions, not measured reference specifications.

The core flow is Home observation preview → Explore target selection → Sky predicted position → Home framing → Save preview → Sessions. Profile holds observer settings, equipment state, night mode, and diagnostics. The camera remains a labeled still-image placeholder.

## Per-image analysis

### R01 — portrait sky atlas with red framing rectangle

- **Layout/hierarchy:** Full-height sky background; compact equipment selector at the top; a tall central field rectangle; zoom controls on the left; a vertical tool rail on the right; partial target dock at the bottom. The sky is primary and the controls occupy its edges.
- **Navigation/components:** Back/collapse control, equipment dropdown, Objects search, Compass, Grid, Ground, Framing, plus/minus zoom, bottom selected-target card.
- **Visual style:** Small neutral sans-serif labels, white line icons, faint cyan constellation lines, orange-red frame, black translucent control backgrounds. The device mockup adds rounded outer corners; it is not necessarily an in-app container. The image supplies most of the depth.
- **Interaction evidence:** Controls imply toggles, selection, and zoom; the image does not show their pressed state or transitions. Proposed behavior: independent toggle state and a persistent selected-target context.
- **UX/adaptation:** Preserve unobstructed content and reachable tools. AstroLearn uses cyan layer toggles and framing on the existing atlas and observation preview, with explicit preview labeling rather than a calibrated field claim.

### R02 — landscape Orion framing view

- **Layout/hierarchy:** Edge-to-edge sky; search at upper left, time centered, orientation control upper right, central rotated rectangle, bottom-right target pill. Labels remain adjacent to stars and nebulae.
- **Navigation/components:** Search, orientation, settings icon, selected M42 card with coordinates, reticle, rotated frame with angular size and rotation labels.
- **Visual style:** Muted blue-gray scientific text, thin red frame, faint teal grid, restrained rounded charcoal dock. Minimal shadows; background imagery dominates.
- **Interaction evidence:** Rotation and dimensions are displayed, but dragging or animation is not visible. Proposed adaptation: a labeled rotation slider with immediate frame feedback.
- **UX/adaptation:** Keep target context while framing. AstroLearn adds frame rotation in a contextual sheet; its frame is explicitly uncalibrated and does not invent angular dimensions.

### R03 — Tonight's Best list and category sidebar

- **Layout/hierarchy:** Dense horizontal catalog rows on the left and a full-height category pane on the right. Each row combines thumbnail, object name, RA/DEC, brightness/size, and an altitude chart.
- **Navigation/components:** Back navigation, category rows with counts, rounded image thumbnails, compact metadata, repeated graph axes.
- **Visual style:** Flat black/charcoal surfaces, green object names, gray secondary text, red graph curves and dashed horizontal guides. Generous row separation offsets high information density.
- **Interaction evidence:** Category selection is implied; no active/hover state or chart tooltip is visible.
- **UX/adaptation:** Support rapid comparison without opening every target. AstroLearn adds category motifs, RA/DEC metadata, and calculated six-hour altitude curves. Categories use the real bundled catalog; no copied inventory counts or fake photographs.

### R04 — map with floating mount control pad

- **Layout/hierarchy:** Immersive tilted sky and horizon; zoom at left; floating right control panel; bottom target dock. Two differently colored frames communicate different pointing contexts.
- **Navigation/components:** Directional pad, speed selector, tracking status, panel collapse chevron, Sync and GoTo actions, target coordinates, map tools.
- **Visual style:** Charcoal translucent rounded panels, large white arrows, amber sky grid, blue and red rectangles. Text uses several levels of emphasis.
- **Interaction evidence:** A direction pad and collapsible panel are visible. Actual movement, continuous press, and tracking behavior cannot be verified.
- **UX/adaptation:** Separate visual guidance from motor actions. AstroLearn adopts contextual framing and collapsible info; physical movement, Sync, and GoTo are deferred until hardware integration.

### R05 — meridian-flip progress and map alignment composite

- **Layout/hierarchy:** Upper screen dims behind a centered task dialog; lower screen retains a full sky with edge tools and a selected-field dock.
- **Navigation/components:** Target/current coordinates, step list with completed and working markers, Cancel; lower Align/GoTo dock and Compass/Grid/Ground tools.
- **Visual style:** Low-key black/gray layers, green progress, thin dividers, rounded modal. Dimmed backdrop creates depth and task focus.
- **Interaction evidence:** Step completion and an in-progress solving state are explicit. Timing, spinner motion, and cancellation semantics are not observable.
- **UX/adaptation:** Explain what the system is doing and distinguish stages. AstroLearn uses an accessible preparation checklist; it does not simulate a successful meridian flip or plate solve in the standalone UI.

### R06 — search list, coordinate picker, and preparation guidance

- **Layout/hierarchy:** Three portrait states: compact catalog, bottom coordinate sheet over the dimmed list, and a guide card over the sky.
- **Navigation/components:** Search/add, Recommend/Favorites tabs, thumbnail rows, favorite and camera actions, RA/DEC wheel-style selection, One-Click GoTo, illustrated instruction, OK/Cancel.
- **Visual style:** Near-black surfaces, gray dividers, green primary CTA, white outlined icons, medium rounded sheets.
- **Interaction evidence:** The composite demonstrates contextual overlays and a preparation checkpoint, but not the transition animation.
- **UX/adaptation:** Progressive disclosure and useful instruction before equipment actions. AstroLearn uses native dialog sheets and a preparation guide; numeric inputs remain more accessible than decorative wheel pickers.

### R07 — catalog rows with visibility states

- **Layout/hierarchy:** Search above tab navigation, then horizontal type chips, then repeatable compact object rows.
- **Navigation/components:** Type dropdown, selected All chip, favorites, imaging shortcuts, expansion chevrons, “Currently invisible” and observing-time metadata.
- **Visual style:** Alternating dark rows, green active chip, white icons, subdued secondary labels. Red annotation boxes are explanatory markup, not interface components.
- **Interaction evidence:** Invisible status and time windows are visible. Expansion behavior is implied; it is not demonstrated.
- **UX/adaptation:** Distinguish availability from identity. AstroLearn keeps above/below-horizon text and numerical altitude. It does not fabricate observing windows or imply geometric altitude guarantees visibility through weather/daylight.

### R08 — Pleiades field preview and framing popover

- **Layout/hierarchy:** Landscape sky with centered rectangular field and dimensions; contextual framing panel overlays the right side in the second state.
- **Navigation/components:** Close, search, frame control, target names, Preview/Tele selector, reset, horizontal/vertical scale settings, ruler slider, estimated mosaic time.
- **Visual style:** Green frame and active icons, amber coordinate grid, charcoal compact panel, pale labels and fine ruler ticks. Selected objects use small luminous points.
- **Interaction evidence:** Open and closed panel states are demonstrated. Slider movement and exact FOV calculation are not demonstrated.
- **UX/adaptation:** Keep composition controls close to the view. AstroLearn adds a framing/preview sheet, rotation slider, and image zoom. Angular field size and mosaic duration remain unavailable without calibration.

### R09 — portrait sky layers menu

- **Layout/hierarchy:** Tall sky canvas, central field box, right edge tools, a compact two-by-two layer menu at the bottom.
- **Navigation/components:** Grid, Labels, Atmosphere, Landscape; frame dimensions, back/search, grid tick labels.
- **Visual style:** Mostly transparent controls, green active line icons, fine brown grid lines, white star names. Red boxes and leader lines are annotations.
- **Interaction evidence:** Layer names and controls are visible; active states beyond green emphasis are ambiguous.
- **UX/adaptation:** Let users control scientific density. AstroLearn provides independent Grid, Labels, and Frame toggles with aria-pressed state. Atmosphere and Landscape are deferred because the current sky model cannot render them faithfully.

### R10 — multi-stage target filtering workflow

- **Layout/hierarchy:** Sequence moves from sky to target list, full filter screen, adjusted filter screen, and resulting list.
- **Navigation/components:** Funnel entry, date/time range, magnitude and altitude sliders, azimuth compass, Save Filter, Reset, Apply, filter-summary header.
- **Visual style:** Green controls over dark panels, fine white labels, compact rows, continuous slider tracks. Tutorial hands and red annotations explain the flow and are not copied.
- **Interaction evidence:** Filter adjustment and application are illustrated by sequential states. No actual transition or live result update is visible.
- **UX/adaptation:** Use draft inputs, Apply, Reset, and persistent preferences. AstroLearn implements minimum altitude, maximum magnitude, cardinal quadrant, Apply/Reset, and saved filters. Unknown magnitude values remain included and are explained.

### R11 — location settings and photo geotag composite

- **Layout/hierarchy:** Settings form uses grouped sections; adjacent photo information screens show metadata and map location.
- **Navigation/components:** Automatic location toggle, latitude/longitude fields with units and helper ranges, location-tag switch, photo Adjust actions, map preview, info/share controls.
- **Visual style:** Black settings surfaces, white labels, gray explanations, green enabled switches; native light photo-detail screens. Red rectangles are annotations.
- **Interaction evidence:** Different coordinates and metadata locations are shown; permission, GPS lookup, and editing flows are not visible.
- **UX/adaptation:** Clear coordinate units and manual entry are retained. AstroLearn connects Profile directly to observer settings. Automatic GPS and photo geotagging remain deferred; diagnostics exclude location by default.

### R12 — log-upload form

- **Layout/hierarchy:** Single-column task page, grouped field rows, large description box, optional attachment region, prominent bottom Submit button.
- **Navigation/components:** Problem selector, log file size, email, optional date, character count, media add control, submission action, back.
- **Visual style:** Dark rounded field groups, compact labels, green pill CTA, fine separators. Red boxes are explanatory annotations.
- **Interaction evidence:** Required/optional structure and attachment limits are visible. Upload success, progress, and validation feedback are not shown.
- **UX/adaptation:** AstroLearn adds problem type, optional date, required bounded description, and local JSON report export. It does not collect email or pretend that a report has been uploaded. Attachments are deferred.

### R13 — landscape camera controls

- **Layout/hierarchy:** Camera feed fills the middle; thumbnail preview upper left; tools on both edges; shutter and parameters on the right; environment/status along the bottom.
- **Navigation/components:** Focus, Tele/Wide, shutter, joystick arrows, gallery, crosshair, camera resolution, exposure status, battery/storage/time.
- **Visual style:** White outlined controls on the image, green selected states, black edge rails, large circular shutter. Control sizes establish action priority.
- **Interaction evidence:** Controls are visible; capture feedback, continuous motion, and focus operation cannot be inferred as implemented.
- **UX/adaptation:** AstroLearn retains the dominant image and large action strip. Save preview adds the source image to Sessions and explicitly does not claim a camera exposure. Battery, sensor temperature, storage, and focus telemetry are not fabricated.

### R14 — camera parameter panel

- **Layout/hierarchy:** Main image region at left, dense settings column at right; large directional pad remains visible.
- **Navigation/components:** Tele/Wide/Settings tabs, filter, shutter, gain selection and ruler, white balance. Selected gain expands its scale.
- **Visual style:** Near-black scene, raised charcoal cards, green active tab, white text/icons, thin divider rhythm. Red selection/arrow annotations are explanatory.
- **Interaction evidence:** Expanded gain adjustment is demonstrated; no numerical hardware response is visible.
- **UX/adaptation:** AstroLearn uses a separate preview settings sheet with working brightness/contrast controls. Hardware gain, exposure, white balance, and motor pad remain unavailable until actual devices exist.

### R15 — gallery selection and image metadata

- **Layout/hierarchy:** Left screen prioritizes bulk selection; right screen prioritizes an image, metadata sheet, and bottom utility bar.
- **Navigation/components:** Selection count, Deselect All/Delete, image checks; exposure/gain/resolution/filter strip, RA/DEC, location, stacking count, temperature, file path/size, download/share/info controls.
- **Visual style:** Dark gallery, green checks, rounded translucent metadata panel, restrained white typography. Red boxes highlight counts for the tutorial.
- **Interaction evidence:** Bulk-selection state and expanded metadata are explicit. Delete confirmation, recovery, or export behavior is not shown.
- **UX/adaptation:** AstroLearn makes preview saving and session lifetime explicit and improves the empty state. Bulk deletion, true stack counts, and device metadata are deferred rather than invented. User-added images keep their names.

### R16 — imaging mode selection

- **Layout/hierarchy:** Live-style camera background and contextual centered/bottom mode chooser in the second state.
- **Navigation/components:** Mode shortcut; closeable image-backed tiles for General, Deep Sky, Solar System, Star Trails, Auto-Capture, Panorama; surrounding shutter/focus/parameter controls.
- **Visual style:** Large rounded modal, image tile backgrounds, white labels/icons, charcoal separators, green active controls. Purple camera imagery supplies ambient color; hands and red boxes are tutorial annotations.
- **Interaction evidence:** The mode sheet opening is shown across the composite. Preset behavior, selected state, and actual capture processing are not visible.
- **UX/adaptation:** AstroLearn provides General/Deep Sky/Solar System/Star Trails preview labels in its settings sheet. They select interface context only; there is no automated capture, panorama, or stacking pipeline in the standalone app.

## Implementation plan and status

| Step | References | AstroLearn adaptation | Current status |
|---|---|---|---|
| 1. Observation hierarchy | R01, R02, R04, R13 | Image-first Home, persistent status, collapsible object education, large bottom actions | Implemented |
| 2. Camera overlays | R01, R02, R08, R09 | Independent crosshair/grid/frame, zoom, local test image, frame rotation | Implemented; uncalibrated composition preview |
| 3. Target comparison | R03, R06, R07 | Existing search/favorites/categories enriched with category motifs, RA/DEC and computed six-hour altitude trends | Implemented |
| 4. Filter flow | R10 | Native sheet, labeled altitude/magnitude/direction, draft Apply/Reset, saved preferences | Implemented |
| 5. Sky layers | R01, R04, R09 | Grid, Labels, and composition Frame controls on calculated atlas | Implemented |
| 6. Guided preparation | R05, R06 | Site → clear field → framing checklist; no fake alignment success | Implemented |
| 7. Imaging disclosure | R08, R13, R14, R16 | Contextual preview modes, brightness/contrast, frame rotation; source image saved to Sessions | Implemented as local preview |
| 8. Observer preferences | R11 | Existing manual location/time form reachable through Profile | Retained and connected |
| 9. Support | R12 | Bounded problem description, optional date/type, local report export without automatic upload | Implemented |
| 10. Session review | R15 | Existing image gallery, source preview save, explicit session lifetime, helpful empty state | Implemented; advanced metadata/bulk tools deferred |
| 11. Hardware integration | R04, R05, R13, R14 | Physical GoTo, joystick, calibration, live camera, gain/exposure/focus | Deferred; requires real hardware adapter |

## State, motion, accessibility, and consistency

Native dialogs provide focus trapping, Escape dismissal, and return focus. All toggle buttons expose aria-pressed; collapse controls expose aria-expanded; status text accompanies color. Inputs are labeled, range output is readable, and control targets use a minimum 44 px height. Native validation bounds numeric and description input. Panels use the same palette, radii, spacing, and button hierarchy across screens. On small screens, dialogs become bottom sheets and the observation columns stack. The persistent navigation remains reachable above the safe content padding.

Suggested motion is a short 150–200 ms opacity/position transition when a sheet or contextual panel opens; this is a recommendation, not a behavior established from the references. Current reduced-motion CSS disables animations and transitions. No ornamental perpetual motion was added. Hover/focus emphasis is a subtle cyan border; keyboard focus uses a visible outline. The atlas also has a textual target list alternative. A full screen-reader and contrast audit has not been completed, so this document does not certify WCAG conformance.

## Verification and limits

JavaScript syntax is checked with Node. Browser verification covers representative navigation, filter-sheet interaction, map layers, and the observation preview; final outcomes are recorded in the accompanying conversation. Source images and overlays are for composition testing. An above-horizon result is a geometric prediction, not a weather or darkness forecast. Six-hour trends use fixed catalog RA/DEC and the observer's chosen time; they are not an ephemeris for moving Solar System targets. Saving a preview preserves the source image, not the display adjustments or an overlay composite. Images in the standalone gallery remain session-only.

Implementation files: user-app/index.html, premium.css, premium.js, refinements.css, refinements.js. The standalone UI is served at http://127.0.0.1:8001/. These changes do not add the same new tools to the separate backend-served interface under astrolearn/static.
