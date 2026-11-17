# AstroLearn — Future Plan

## Arabic and Islamic astronomy — planned

Status: planned, not installed. Preserve the current cyan/violet observation UI. Backup_1.zip contains the current user-app and astrolearn/static directories with SHA-256 checksums in BACKUP_MANIFEST.json. It is a UI backup, not a backup of databases, solver catalogs, or the whole project.

- Add an Arabic/English switch with a saved language preference.
- Support right-to-left layout while preserving sky-map geometry, camera imagery, and scientific coordinates.
- Translate navigation, controls, settings, dialogs, errors, accessibility labels, and educational catalog descriptions; verify dynamic messages as well as static text.
- Show Hijri and Gregorian dates together. Identify the calendar method (initial proposal: Umm al-Qura), timezone, and civil-date rollover. Explain that local moon-sighting dates may differ; do not imply sunset rollover unless implemented.
- Add Qibla bearing calculated from validated observer coordinates, measured clockwise from true north. Label it as a calculated bearing, not a live compass.
- Add concise Arabic/English educational notes about the lunar calendar and crescent observation. Calendar dates alone must not be presented as proof of crescent visibility.
- Keep prayer times as a separate future decision requiring an agreed calculation method and location/timezone handling.

### Implementation and acceptance

1. Review the prepared AstroLearn_Arabic_Update.zip as a starting point; it has not been installed in this project.
2. Integrate localization into the current UI without replacing the observation layout.
3. Test language switching, persistence, dynamically generated content, keyboard navigation, Arabic labels, and mobile RTL layouts.
4. Test Hijri dates around midnight/timezone changes and validate Qibla calculations for several locations and invalid inputs.
5. Verify overlays, filters, image loading, and session navigation after integration.

Prepared update: https://chatgpt.com/library?file_id=libfile_7faa9379a4088191a7a9eec1b82c83f7&account_id=personal
