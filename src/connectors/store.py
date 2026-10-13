"""Snapshots of what the banks show, in a database of their own.

Standard library only, plain dicts out, like src/databases/sqlite.py - but a
separate file, so the connectors never touch the app's database.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, model_validator

from src.connectors.paths import DB_PATH

# Re-exported so callers can say store.DEFAULT_DB.
DEFAULT_DB = DB_PATH
SCHEMA_PATH = Path(__file__).parent / "schema.sql"


class PositionRow(BaseModel):
    """One line of a snapshot, whatever the bank."""

    model_config = ConfigDict(frozen=True)

    account: str
    support_type: str
    # Stable identity of the line, filled in by the validator when the caller
    # does not set it: the ISIN, or "account|label" when the broker does not
    # tag the holding (a part-based CEFP line without ISIN).
    broker_key: str | None = None
    isin: str | None = None
    label: str
    quantity: float | None = None
    value: float
    currency: str = "EUR"
    unit_cost: float | None = None
    unit_price: float | None = None
    gain: float | None = None

    @model_validator(mode="before")
    @classmethod
    def _fill_broker_key(cls, data: Any) -> Any:
        if isinstance(data, dict) and not data.get("broker_key"):
            data["broker_key"] = data.get("isin") or (
                f"{data.get('account', '')}|{data.get('label', '')}"
            )
        return data


def connect(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    connection.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
    # Snapshots taken before the line identity existed lack the column.
    columns = {
        row["name"] for row in connection.execute("PRAGMA table_info(positions)")
    }
    if "broker_key" not in columns:
        connection.execute(
            "ALTER TABLE positions ADD COLUMN broker_key TEXT NOT NULL DEFAULT ''"
        )
    return connection


def save_snapshot(
    path: Path, source: str, rows: list[PositionRow], taken_at: str | None = None
) -> int:
    """Insert a snapshot and its lines in one transaction; return its id."""
    taken_at = taken_at or datetime.now(timezone.utc).isoformat(timespec="seconds")
    connection = connect(path)
    try:
        with connection:
            snapshot_id = connection.execute(
                "INSERT INTO snapshots (source, taken_at) VALUES (?, ?)",
                (source, taken_at),
            ).lastrowid
            connection.executemany(
                """
                INSERT INTO positions (
                    snapshot_id, account, support_type, broker_key, isin, label,
                    quantity, value, currency, unit_cost, unit_price, gain
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        snapshot_id,
                        r.account,
                        r.support_type,
                        r.broker_key,
                        r.isin,
                        r.label,
                        r.quantity,
                        r.value,
                        r.currency,
                        r.unit_cost,
                        r.unit_price,
                        r.gain,
                    )
                    for r in rows
                ],
            )
        return snapshot_id
    finally:
        connection.close()


def snapshots(path: Path, source: str) -> list[dict[str, Any]]:
    connection = connect(path)
    try:
        return [
            dict(row)
            for row in connection.execute(
                "SELECT * FROM snapshots WHERE source = ? ORDER BY taken_at, id",
                (source,),
            )
        ]
    finally:
        connection.close()


def latest(path: Path, source: str) -> list[dict[str, Any]]:
    """The lines of the most recent snapshot of a source, or nothing."""
    connection = connect(path)
    try:
        return [
            dict(row)
            for row in connection.execute(
                """
                SELECT p.* FROM positions p
                WHERE p.snapshot_id = (
                    SELECT id FROM snapshots WHERE source = ?
                    ORDER BY taken_at DESC, id DESC LIMIT 1
                )
                ORDER BY p.rowid
                """,
                (source,),
            )
        ]
    finally:
        connection.close()
