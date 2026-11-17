"""Small SQLite repository; user input is always passed as SQL parameters."""

import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path

from astrolearn.models import Observation, ObservationCreate


class ObservationStore:
    def __init__(self, path: Path):
        self.path = path

    def initialize(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with closing(sqlite3.connect(self.path)) as conn, conn:
            conn.execute("""CREATE TABLE IF NOT EXISTS observations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                target TEXT NOT NULL, notes TEXT NOT NULL,
                created_at TEXT NOT NULL)""")

    def create(self, item: ObservationCreate) -> Observation:
        timestamp = datetime.now(timezone.utc)
        # A connection per operation avoids sharing thread-bound SQLite connections.
        with closing(sqlite3.connect(self.path)) as conn, conn:
            cursor = conn.execute(
                "INSERT INTO observations (target, notes, created_at) VALUES (?, ?, ?)",
                (item.target, item.notes, timestamp.isoformat()),
            )
            return Observation(id=cursor.lastrowid, created_at=timestamp, **item.model_dump())

    def list(self, limit: int, offset: int) -> list[Observation]:
        with closing(sqlite3.connect(self.path)) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM observations ORDER BY id DESC LIMIT ? OFFSET ?",
                (limit, offset),
            ).fetchall()
            return [Observation(**dict(row)) for row in rows]

    def get(self, observation_id: int) -> Observation | None:
        with closing(sqlite3.connect(self.path)) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT * FROM observations WHERE id = ?", (observation_id,)
            ).fetchone()
            return Observation(**dict(row)) if row else None
