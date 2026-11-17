# Imported source baseline

The working local prototype, documentation, dependency manifests, setup scripts,
tests, UI assets, local identification catalogs, and UI/UX design brief were
imported on 17 November 2026.

## Current layout

- `astrolearn/`: working Python application, API, static UI, astronomy, image
  processing, local solver integrations, identification, persistence, and mount simulation.
- `user-app/`: standalone UI prototype, with its own README.
- `tests/`, `scripts/`, `benchmarks/`: regression tests, setup and diagnostic tools,
  and benchmark source registry.
- `docs/`: design decisions, implementation notes, verification reports, and previews.
- `resources/*.json`: local-resource provenance and installation metadata.
- `samples/`: synthetic demo and solar examples; survey test-pack instructions
  and manifest are included.

The original component folders and architecture proposal remain as a roadmap.
Preserve the working layout until imports, asset paths, and API contracts are
updated together. Existing solver integrations perform real local work; physical
camera capture and mount movement remain hardware-dependent or simulated.

## Setup and local assets

Follow the root README for installation and launch. Downloaded ASTAP/Siril tools,
solver catalogs, ephemerides, optional model weights, the virtual environment,
local databases/uploads, temporary files, duplicate sample packs, and ZIP backups
are excluded. The original report is supplied separately. The UI/UX design brief
is included at the repository root.

Large survey FITS inputs, derived survey PNGs, and benchmark output files were not
included in this source import. Use `scripts/prepare_solver_test_set.py` and the
sample README/manifest to recreate the survey test pack before running its benchmark.
External resources are needed for full offline solving and optional integrations;
install them on the target machine before disconnecting it from the network.
