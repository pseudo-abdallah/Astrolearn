# Work packages

Each package can be developed in a separate chat or by a different teammate. Share the root README, this file, and shared/README.md with every contributor.

| Package | Owned folders | Deliverable | Acceptance |
| --- | --- | --- | --- |
| 1 — UI | ui/ | Existing UI imported, preview and status integration | Loading, disconnect, error, and cancellation states work with a mock backend |
| 2 — Backend and local solving | backend/, camera/, plate_solver/, shared/ | Local capture-to-solve pipeline and API contracts | A local test image produces a result or explicit failure; timeout and disconnect paths work |
| 3 — Mount and imaging | mount_control/, image_processing/, tests/ | Device adapter, controlled pointing, calibration and integration checks | Simulated mount commands respect limits and stop behavior; originals remain unchanged |
| 4 — Optional AI | ai/ | Local enhancement with separate derived output | Core operation works when AI is absent or disabled |

## Integration order

1. Import and verify the existing application.
2. Agree on shared request, response, event, coordinate, and frame metadata.
3. Connect the UI to simulated backend jobs.
4. Integrate local camera capture and solver.
5. Integrate mount control with a simulator before physical hardware.
6. Add image processing and optional enhancement.

Package 4 is optional. Packages 1–3 should deliver a usable core platform without it.

Each handoff must state changed paths, launch instructions, dependencies, checks performed, remaining placeholders, and required configuration. Do not invent working endpoints or dependencies before implementing them.
