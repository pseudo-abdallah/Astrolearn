# Foundation design and acceptance criteria

## Architecture

API client → FastAPI routes → validated models → SQLite observation repository.
The status route also reads a hardware adapter. Its default implementation
reports disconnected and performs no physical operation. Each application
instance owns its adapter and repository; tests can inject a temporary database.

The API namespace is `/api/v1`. OpenAPI is generated from the route contracts.
Database creation happens at application startup, not import time. Each storage
operation opens and closes its own connection and writes inside a transaction.
Timestamps use UTC. Parameterized SQL treats target names and notes as data.
SQLite is a minimal local persistence choice, not a claim about the final design.

The three educational catalog entries are sample content. They have no sky
coordinates, live visibility, pointing commands, or promised telescope performance.
An observation is a manually entered journal record. The schema intentionally
does not invent exposure settings, measured coordinates, or captured image paths.

## Acceptance criteria

| Phase | Criterion | Evidence |
|---|---|---|
| 1 | Reproducible local setup instructions | README, requirements, project metadata |
| 1 | Laptop and Pi commands supplied | README; Pi hardware execution remains unverified |
| 1 | Separate application modules and tests | `astrolearn/`, `tests/` |
| 2 | API starts without hardware | Disconnected adapter and startup tests |
| 2 | Basic educational data is readable | Catalog and lookup tests |
| 2 | Notes validate and persist | Round-trip, invalid input, restart tests |
| 2 | Unsupported hardware is reported accurately | Capability test; no control endpoints |
| 2 | API contracts are inspectable | `/docs`, `/openapi.json`, schema test |

## Items requiring confirmation

Review the uploaded capstone and final team requirements when accessible. Confirm
the Raspberry Pi model and OS, telescope mount, whether camera or powered motion
exists, exact interfaces and electrical limits, intended student workflow, and
whether access is local or networked. These are open questions, not requirements
that this scaffold assumes. Hardware adapters and commands should follow those
answers. A frontend and hardware integration are outside these two phases.

The existing report-access and tmp helper folders were left intact; they are
unrelated to the backend runtime.
