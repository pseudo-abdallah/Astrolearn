# Import validation — 17 November 2026

All 119 imported files were checked against their local Git blob hashes before publication.

Validation in the existing Windows environment:

- Four focused tests passed: both camera benchmark tests, invalid/missing WCS rejection, and native solver timeout-log retention.
- `python -m compileall -q astrolearn scripts tests` completed successfully. An existing invalid-escape SyntaxWarning was reported in the Siril installer docstring.
- The full pytest run stalled before the first API test completed. A diagnostic run located the stall in Windows asyncio socket-pair creation (`socket.accept`), invoked by Starlette TestClient. Both stalled runs were stopped. Full-suite success is not claimed.

Run the full suite in an environment where local asyncio sockets work, with the external solver resources installed for integration coverage. Historical verification documents describe earlier runs, not this import validation.
