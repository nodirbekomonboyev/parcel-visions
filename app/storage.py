"""Natijalarni saqlash. Hozir SQLite — qo'shimcha hech narsa o'rnatish shart emas.

MongoDB'ga o'tish uchun shu fayldagi uchta metodni almashtirish yetarli.
"""
import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import List

from app.schema import ExtractionResult, LabelData

DB_PATH = Path(os.getenv("DB_PATH", "data/extractions.db"))

_SCHEMA = """
CREATE TABLE IF NOT EXISTS extractions (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    provider   TEXT NOT NULL,
    model      TEXT NOT NULL,
    filename   TEXT NOT NULL,
    took_ms    INTEGER NOT NULL,
    payload    TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_extractions_created ON extractions(created_at DESC);
"""


def _connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init() -> None:
    with _connect() as conn:
        conn.executescript(_SCHEMA)


def save(result: ExtractionResult) -> int:
    created = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with _connect() as conn:
        cur = conn.execute(
            "INSERT INTO extractions (provider, model, filename, took_ms, payload, created_at)"
            " VALUES (?, ?, ?, ?, ?, ?)",
            (result.provider, result.model, result.filename, result.took_ms,
             result.data.model_dump_json(), created),
        )
        return int(cur.lastrowid)


def recent(limit: int = 50) -> List[ExtractionResult]:
    with _connect() as conn:
        rows = conn.execute(
            "SELECT * FROM extractions ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
    return [
        ExtractionResult(
            id=r["id"], provider=r["provider"], model=r["model"],
            filename=r["filename"], took_ms=r["took_ms"],
            data=LabelData.model_validate(json.loads(r["payload"])),
            created_at=r["created_at"],
        )
        for r in rows
    ]
