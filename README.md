# AstroLearn

Local-first astrophotography platform — graduation project.

## Current status

This repository contains the project structure and implementation guidance. Application source code has not yet been imported. The camera pipeline, plate solver, mount controller, and AI enhancement are not implemented here yet.

## Repository structure

| Directory | Responsibility |
| --- | --- |
| ui/ | User interface, live preview, controls, and status |
| backend/ | API, jobs, orchestration, configuration, and persistence |
| camera/ | Device adapters, capture, and frame metadata |
| plate_solver/ | Local solver integration and coordinate results |
| mount_control/ | Mount adapters, pointing, tracking, and stop handling |
| image_processing/ | Calibration, quality checks, registration, and stacking |
| ai/ | Optional local image enhancement |
| shared/ | Versioned API and event contracts |
| docs/ | Architecture, setup, and work packages |
| tests/ | Cross-component integration and end-to-end tests |
| scripts/ | Development and setup utilities |
| config/ | Non-secret example configuration |

## Start here

1. Read [architecture](docs/architecture.md).
2. Choose a [work package](docs/work-packages.md).
3. Follow the [source import checklist](docs/source-import.md).
4. Agree on [shared contracts](shared/README.md) before connecting components.

Core processing must work locally without cloud services. Keep raw captures unchanged; generated previews and enhancements are derived outputs. AI is optional and must not block capture, plate solving, or mount control.

No installation or launch command is provided yet because executable source and dependency manifests have not been imported.
