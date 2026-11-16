# Backend

Owns the API, job lifecycle, orchestration, configuration, and local persistence. Coordinate camera, solver, mount, and imaging modules through explicit interfaces.

Suggested internal areas: api/, jobs/, services/, and database/. Heavy processing should run outside request handlers. Persist job status and publish progress events to the UI.

Use port 8001 for local development when implementing launch configuration. Actual framework and dependency files must come from the inspected application.

Status: implementation/import pending.
