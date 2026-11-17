"""Persist uploaded-image metadata, solve jobs and observation sessions."""

from contextlib import closing
from datetime import datetime, timezone
import json
import hashlib
from pathlib import Path
import sqlite3
from uuid import uuid4


class PrototypeStore:
    def __init__(self, database: Path):
        self.database = database
        self.files = database.parent / "images"

    def initialize(self):
        self.files.mkdir(parents=True, exist_ok=True)
        with closing(sqlite3.connect(self.database)) as conn, conn:
            conn.execute("CREATE TABLE IF NOT EXISTS prototype_records (id TEXT PRIMARY KEY, kind TEXT NOT NULL, payload TEXT NOT NULL)")
            # Work cannot continue after restart; never leave a perpetual spinner.
            for key, payload in conn.execute("SELECT id,payload FROM prototype_records WHERE kind IN ('solve','analysis')").fetchall():
                item = json.loads(payload)
                if item['status'] in {'queued', 'running'}:
                    item.update(status='failed', message='Server restarted; submit a new solve.')
                    conn.execute("UPDATE prototype_records SET payload=? WHERE id=?", (json.dumps(item), key))

    def save(self, kind: str, record: dict) -> dict:
        with closing(sqlite3.connect(self.database)) as conn, conn:
            conn.execute("INSERT OR REPLACE INTO prototype_records VALUES (?,?,?)", (record['id'], kind, json.dumps(record, allow_nan=False)))
        return record

    def new(self, kind: str, **values) -> dict:
        return self.save(kind, {"id": uuid4().hex, "created_at": datetime.now(timezone.utc).isoformat(), **values})

    def get(self, kind: str, key: str) -> dict | None:
        with closing(sqlite3.connect(self.database)) as conn:
            row = conn.execute("SELECT payload FROM prototype_records WHERE kind=? AND id=?", (kind, key)).fetchone()
            return json.loads(row[0]) if row else None

    def list(self, kind: str, limit: int = 100, offset: int = 0) -> list[dict]:
        with closing(sqlite3.connect(self.database)) as conn:
            rows = conn.execute("SELECT payload FROM prototype_records WHERE kind=? ORDER BY rowid DESC LIMIT ? OFFSET ?", (kind, limit, offset)).fetchall()
            return [json.loads(row[0]) for row in rows]

    def latest_for_image(self, kind: str, image_id: str) -> dict | None:
        with closing(sqlite3.connect(self.database)) as conn:
            row = conn.execute("SELECT payload FROM prototype_records WHERE kind=? AND json_extract(payload, '$.image_id')=? ORDER BY rowid DESC LIMIT 1", (kind, image_id)).fetchone()
            return json.loads(row[0]) if row else None

    def successful_solve(self, image_id: str) -> dict | None:
        """Recover real WCS only for this image or byte-identical originals.

        A failed retry must not hide a previous success. File comparison also
        supports uploads made before fingerprints were stored, without using a
        filename, selected target or visual resemblance as evidence of identity.
        """
        image = self.get('image', image_id)
        if image is None:
            return None
        with closing(sqlite3.connect(self.database)) as conn:
            rows = conn.execute("""SELECT s.payload, i.payload FROM prototype_records s
                JOIN prototype_records i ON i.id=json_extract(s.payload,'$.image_id')
                WHERE s.kind='solve' AND i.kind='image'
                AND json_extract(s.payload,'$.status')='solved'
                ORDER BY s.rowid DESC""").fetchall()
        digest = None
        for payload, image_payload in rows:
            solved, candidate = json.loads(payload), json.loads(image_payload)
            if solved['image_id'] == image_id:
                return solved
            try:
                if digest is None:
                    digest = hashlib.sha256((self.files/image['original']).read_bytes()).digest()
                other = hashlib.sha256((self.files/candidate['original']).read_bytes()).digest()
                if digest == other:
                    return solved
            except OSError:
                continue
        return None
