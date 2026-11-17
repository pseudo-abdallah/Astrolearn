# Verification record

Verified on Windows with Python 3.12.14 on November 2, 2026.

Command: `.venv/Scripts/python.exe -m pytest -q --tb=short`

Result: **15 passed**. One upstream Starlette/AnyIO deprecation warning was
reported; it did not affect the results. Tests needed normal Windows temporary
folder access because the restricted runner could not create test directories.

Dependency check: `python -m pip check` reported no broken requirements.
A real Uvicorn process was also started on localhost port 8765; HTTP health
returned `{"status":"ok","version":"0.1.0"}`. The process was stopped after
the check. Normal Windows access was required for this startup check as well.

Coverage includes health and truthful hardware status, catalog retrieval and
404s, creation and retrieval of observations, pagination, invalid input rejection,
database persistence across application restarts, database isolation, SQL-like
input stored literally, and generated OpenAPI documentation.

Raspberry Pi execution and physical hardware operation have not been tested.
Capstone PDF review remains pending because uploaded-file retrieval was
unavailable. This record does not claim capstone compliance or hardware readiness.
