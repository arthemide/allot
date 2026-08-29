"""SQLite access. Standard library only, no ORM.

Every read returns plain dicts; no derived state is ever stored,
so there is nothing to keep in sync.
"""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path
from typing import Any, Iterator

ROOT = Path(__file__).parent.parent.parent

# Overridable so the database can live on a mounted volume, outside the tree.
DB_PATH = Path(os.getenv("ALLOT_DB_PATH", ROOT / "data" / "allot.db"))
SCHEMA_PATH = ROOT / "schema.sql"


def connect(path: Path = DB_PATH) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def init(path: Path = DB_PATH) -> None:
    """Create the schema if the database is empty. Safe to call on every boot."""
    connection = connect(path)
    try:
        connection.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
        connection.commit()
    finally:
        connection.close()


def query(sql: str, params: tuple = ()) -> list[dict[str, Any]]:
    connection = connect()
    try:
        return [dict(row) for row in connection.execute(sql, params)]
    finally:
        connection.close()


def execute(sql: str, params: tuple = ()) -> int:
    """Run a write and return the last inserted row id."""
    connection = connect()
    try:
        cursor = connection.execute(sql, params)
        connection.commit()
        return cursor.lastrowid or 0
    finally:
        connection.close()


# --- assets ---------------------------------------------------------------


def all_assets() -> list[dict[str, Any]]:
    return query("SELECT * FROM asset ORDER BY envelope, symbol")


def get_asset(symbol: str) -> dict[str, Any] | None:
    rows = query("SELECT * FROM asset WHERE symbol = ?", (symbol,))
    return rows[0] if rows else None


def add_asset(
    symbol: str, label: str, envelope: str, currency: str, weight: float = 1.0
) -> None:
    execute(
        """
        INSERT INTO asset (symbol, label, envelope, currency, weight)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(symbol) DO UPDATE SET
            label = excluded.label,
            envelope = excluded.envelope,
            currency = excluded.currency,
            weight = excluded.weight
        """,
        (symbol, label, envelope, currency, weight),
    )


def update_asset(symbol: str, label: str, envelope: str, weight: float) -> None:
    execute(
        "UPDATE asset SET label = ?, envelope = ?, weight = ? WHERE symbol = ?",
        (label, envelope, weight, symbol),
    )


def set_opening_position(symbol: str, quantity: float, invested: float | None) -> None:
    """Record a holding that predates tracking: a quantity and what it cost.

    A statement gives the number of units and the total paid, so the PRUM is
    derived rather than asked for. Passing a quantity of 0 clears it.
    """
    if quantity <= 0 or not invested:
        execute(
            "UPDATE asset SET base_quantity = 0, base_prum = NULL WHERE symbol = ?",
            (symbol,),
        )
        return
    execute(
        "UPDATE asset SET base_quantity = ?, base_prum = ? WHERE symbol = ?",
        (quantity, invested / quantity, symbol),
    )


def delete_asset(symbol: str) -> None:
    """Transactions go with it, through ON DELETE CASCADE."""
    execute("DELETE FROM asset WHERE symbol = ?", (symbol,))


# --- envelopes ------------------------------------------------------------


def all_envelopes() -> list[dict[str, Any]]:
    return query("SELECT * FROM envelope ORDER BY name")


def get_envelope(name: str) -> dict[str, Any] | None:
    rows = query("SELECT * FROM envelope WHERE name = ?", (name,))
    return rows[0] if rows else None


def upsert_envelope(name: str, monthly_amount: float) -> None:
    execute(
        """
        INSERT INTO envelope (name, monthly_amount) VALUES (?, ?)
        ON CONFLICT(name) DO UPDATE SET monthly_amount = excluded.monthly_amount
        """,
        (name, monthly_amount),
    )


def delete_envelope(name: str) -> None:
    execute("DELETE FROM envelope WHERE name = ?", (name,))


def envelope_asset_count(name: str) -> int:
    return query("SELECT count(*) AS n FROM asset WHERE envelope = ?", (name,))[0]["n"]


def prune_empty_envelopes() -> list[str]:
    """Drop envelopes that no longer hold anything.

    Envelopes are only ever created by adding an asset to them, so one left
    empty is a leftover, never a deliberate placeholder.
    """
    empty = [
        row["name"]
        for row in query(
            """
            SELECT name FROM envelope
            WHERE name NOT IN (SELECT DISTINCT envelope FROM asset)
            """
        )
    ]
    for name in empty:
        delete_envelope(name)
    return empty


# --- transactions ---------------------------------------------------------


def transactions_of(symbol: str) -> list[dict[str, Any]]:
    return query(
        'SELECT * FROM "transaction" WHERE symbol = ? ORDER BY date, id', (symbol,)
    )


def all_transactions() -> list[dict[str, Any]]:
    return query('SELECT * FROM "transaction" ORDER BY date, id')


def add_transaction(
    symbol: str,
    date: str,
    side: str,
    quantity: float,
    unit_price: float,
    fees: float = 0.0,
) -> int:
    return execute(
        """
        INSERT INTO "transaction" (symbol, date, side, quantity, unit_price, fees)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (symbol, date, side, quantity, unit_price, fees),
    )


def delete_transaction(transaction_id: int) -> None:
    execute('DELETE FROM "transaction" WHERE id = ?', (transaction_id,))


def last_transaction_date() -> str | None:
    rows = query('SELECT max(date) AS last FROM "transaction"')
    return rows[0]["last"] if rows else None


# --- price cache ----------------------------------------------------------


def cached_prices(symbol: str) -> list[dict[str, Any]]:
    return query(
        "SELECT date, price FROM price_cache WHERE symbol = ? ORDER BY date",
        (symbol,),
    )


def cache_prices(symbol: str, points: Iterator[tuple[str, float]]) -> None:
    connection = connect()
    try:
        connection.executemany(
            """
            INSERT INTO price_cache (symbol, date, price) VALUES (?, ?, ?)
            ON CONFLICT(symbol, date) DO UPDATE SET price = excluded.price
            """,
            ((symbol, date, price) for date, price in points),
        )
        connection.commit()
    finally:
        connection.close()
