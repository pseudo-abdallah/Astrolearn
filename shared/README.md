# Shared contracts

This directory will hold versioned schemas and contract documentation shared by UI and backend components. No API schema is implemented yet.

Agree on the following before integrating modules:

- Job identifiers, states, progress, timestamps, cancellation, and errors.
- Frame identifiers, local references, dimensions, pixel format, exposure, and capture time.
- Solve results, coordinate frames, angular units, orientation, and scale.
- Device connection state, capabilities, motion state, and command acknowledgements.
- Event version, event ID, job correlation, and reconnect behavior.

Suggested job states: queued, running, succeeded, failed, cancelled. Define legal transitions in implementation. Distinguish a request to cancel from a confirmed cancellation.

Do not expose unrestricted filesystem paths to the browser. Use backend-controlled frame IDs for image retrieval.
