# AstroLearn — phases 1 and 2

A working Python backend foundation for a Raspberry Pi educational telescope.
Develop on a laptop first; this version needs no connected telescope hardware.
Python 3.11+ is required (verified here with Python 3.12).

## Scope and source context

The referenced **Software Development Guidance** chat was read. It proposes a
Python backend on Raspberry Pi, an educational interface, and later hardware
integration; it explicitly calls that architecture provisional. Its available
text does not define the individual phases in detail. This implementation uses
the phase definitions in your current request.

The workspace contains a prior library reference to `AstroLearn.pdf`, but the
PDF itself is absent and the file service reported that retrieval was unavailable.
Consequently, no capstone-specific component, pin assignment, camera, motor,
tracking method, or requirement is claimed as confirmed here. The capstone
documents must still be reviewed before hardware integration or final report
alignment. See [design notes](docs/design.md).

## Phase 1: environment and scaffold

From this project folder on Windows PowerShell:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m uvicorn astrolearn.main:app --host 127.0.0.1 --port 8000
```

On Raspberry Pi OS/Linux with Python 3.11+ and the Python venv package installed:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-dev.txt
.venv/bin/python -m pytest -q
.venv/bin/python -m uvicorn astrolearn.main:app --host 127.0.0.1 --port 8000
```

Use `requirements.txt` instead for runtime dependencies only. Activation is
optional because these commands select the environment's Python directly.
Direct dependencies are pinned; transitive dependencies are not fully locked.

Open [interactive API documentation](http://127.0.0.1:8000/docs) to try endpoints,
or [health](http://127.0.0.1:8000/api/v1/health). Stop with Ctrl+C.
If `py` is unavailable, install Python 3.11+ or substitute its full executable
path. A Python installation with pip and venv is needed for these setup commands.

## Phase 2: backend foundation

| Method | Path | Behavior |
|---|---|---|
| GET | `/` | Project name, version, documentation link |
| GET | `/api/v1/health` | API process health; does not claim hardware health |
| GET | `/api/v1/status` | Disconnected hardware and supported capabilities |
| GET | `/api/v1/objects` | Three illustrative educational entries |
| GET | `/api/v1/objects/{object_id}` | One entry, or 404 |
| POST | `/api/v1/observations` | Validate and save a user-entered note; 201 |
| GET | `/api/v1/observations` | Newest first; `limit=1..100`, `offset>=0` |
| GET | `/api/v1/observations/{observation_id}` | Saved note, or 404 |
| GET | `/openapi.json` | Machine-readable API specification |

Example in PowerShell while the server is running:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/v1/status
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/api/v1/observations -ContentType 'application/json' -Body '{"target":"Moon","notes":"Practice observation log entry"}'
Invoke-RestMethod http://127.0.0.1:8000/api/v1/observations
```

Observation requests accept `target` (1–120 characters after trimming) and
`notes` (optional, up to 4000 characters). Unknown fields and invalid input return
422. Saved records include an integer ID and a UTC timestamp. Notes are manual
records, not evidence of a hardware capture or an automated observation.

SQLite storage is created on startup at `data/astrolearn.sqlite3`, relative to
the folder from which you launch the server. Records survive restarts. To choose
a location, set the environment variable before starting:

```powershell
$env:ASTROLEARN_DB_PATH = 'data/demo.sqlite3'
```

This variable is read from the process environment; `.env` files are not loaded.
No database server or network connection is required during normal operation.

## Files and verification

```text
astrolearn/
  main.py       Application factory, startup and API routes
  models.py     Validated request and response models
  storage.py    SQLite persistence and parameterized queries
  hardware.py   Adapter boundary and disconnected implementation
tests/
  test_api.py   API, validation, persistence and isolation tests
docs/
  design.md     Design decisions, boundaries and acceptance criteria
requirements.txt / requirements-dev.txt / pyproject.toml
```

Tests use temporary databases, never the normal observation file. They cover
health, truthful disconnected status, catalog lookup, missing resources, input
validation, pagination, restart persistence, database isolation, SQL-like input,
and API documentation. The testing approach follows the
[official FastAPI testing guide](https://fastapi.tiangolo.com/tutorial/testing/).

This is a local development prototype: no login, browser interface, image
capture, motors, automatic pointing, visibility calculations, or GPIO drivers.
The server binds to localhost by default. Authentication and deployment decisions
remain future work before sharing access on a network. Hardware behavior needs
confirmed components and integration tests on the actual Raspberry Pi.
