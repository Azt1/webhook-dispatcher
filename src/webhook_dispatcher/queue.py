from __future__ import annotations

import sqlite3
import time
import uuid
from contextlib import closing
from pathlib import Path

from .events import validate_event


class EventQueue:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with closing(self._connect()) as db, db:
            db.execute("""
                CREATE TABLE IF NOT EXISTS events (
                    id TEXT PRIMARY KEY,
                    url TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'pending',
                    attempts INTEGER NOT NULL DEFAULT 0,
                    created_at REAL NOT NULL,
                    next_attempt REAL NOT NULL,
                    last_error TEXT,
                    http_status INTEGER
                )
            """)

    def _connect(self):
        db = sqlite3.connect(self.path)
        db.row_factory = sqlite3.Row
        return db

    def add(self, url: str, payload: dict) -> str:
        body = validate_event(url, payload)
        event_id = str(uuid.uuid4())
        now = time.time()
        with closing(self._connect()) as db, db:
            db.execute(
                "INSERT INTO events (id, url, payload, created_at, next_attempt) VALUES (?, ?, ?, ?, ?)",
                (event_id, url, body, now, now),
            )
        return event_id

    def list(self, status: str | None = None) -> list[dict]:
        if status is not None and status not in {"pending", "delivered", "failed"}:
            raise ValueError("Status inválido")
        with closing(self._connect()) as db:
            if status is None:
                rows = db.execute("SELECT * FROM events ORDER BY created_at, id")
            else:
                rows = db.execute(
                    "SELECT * FROM events WHERE status = ? ORDER BY created_at, id", (status,)
                )
            return [dict(row) for row in rows]

    def ready(self, now: float | None = None, limit: int = 100) -> list[dict]:
        if limit < 1:
            raise ValueError("O limite precisa ser maior que zero")
        with closing(self._connect()) as db:
            rows = db.execute(
                "SELECT * FROM events WHERE status = 'pending' AND next_attempt <= ? "
                "ORDER BY created_at, id LIMIT ?",
                (time.time() if now is None else now, limit),
            )
            return [dict(row) for row in rows]

    def record(self, event_id: str, status: str, http_status: int | None = None,
               error: str | None = None, next_attempt: float = 0):
        if status not in {"pending", "delivered", "failed"}:
            raise ValueError("Status inválido")
        with closing(self._connect()) as db, db:
            result = db.execute(
                "UPDATE events SET status = ?, attempts = attempts + 1, http_status = ?, "
                "last_error = ?, next_attempt = ? WHERE id = ?",
                (status, http_status, error, next_attempt, event_id),
            )
            if result.rowcount != 1:
                raise ValueError("Evento não encontrado")
