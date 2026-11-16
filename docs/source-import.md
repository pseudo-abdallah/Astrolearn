# Importing existing source

The existing project archive has not been imported into this repository.

1. Inspect the latest AstroLearn source archive and identify the real entry points, assets, dependency manifests, and backend routes.
2. Inspect files for secrets and machine-specific paths before upload, since this repository is public.
3. Move the existing frontend into ui/ while preserving its framework layout and asset relationships.
4. Move existing API and orchestration code into backend/. Extract camera, solver, and mount adapters only after identifying their imports and runtime behavior.
5. Update relative paths, frontend API base configuration, static asset handling, and launch scripts.
6. Preserve the requested local backend port 8001 unless the project configuration requires an agreed change.
7. Run the existing build or smoke checks, then verify preview loading and API connectivity.
8. Replace placeholder README sections with the actual install and run commands.

Do not commit archives, generated dependency folders, raw observation sessions, or solver indexes as substitutes for source code.
