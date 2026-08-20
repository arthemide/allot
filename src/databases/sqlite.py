"""SQLite access. Standard library only, no ORM.

Every read returns plain dicts; no derived state is ever stored,
so there is nothing to keep in sync.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any, Iterator

ROOT = Path(__file__).parent.parent.parent
DB_PATH = ROOT / "data" / "wealth.db"
SCHEMA_PATH = ROOT / "schema.sql"


def connect(path: Path = DB_PATH) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


SCHEMA_VERSION = 2

# One entry per schema version above 1, applied to databases created before it.
# schema.sql alone covers a fresh database.
UPGRADES: dict[int, list[str]] = {
    2: ["ALTER TABLE asset ADD COLUMN actual_quantity REAL"],
}


def init(path: Path = DB_PATH) -> None:
    """Create the schema, or bring an older database up to date.

    Safe to call on every boot: creating tables is guarded by IF NOT EXISTS and
    upgrades only run for versions the database has not reached yet.
    """
    connection = connect(path)
    try:
        version = connection.execute("PRAGMA user_version").fetchone()[0]
        has_tables = connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'asset'"
        ).fetchone()
        if has_tables:
            for step in range(version + 1, SCHEMA_VERSION + 1):
                for statement in UPGRADES.get(step, []):
                    connection.execute(statement)
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


def upsert_asset(
    symbol: str, label: str, envelope: str, currency: str, price_source: str
) -> None:
    execute(
        """
        INSERT INTO asset (symbol, label, envelope, currency, price_source)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(symbol) DO UPDATE SET
            label = excluded.label,
            envelope = excluded.envelope,
            currency = excluded.currency,
            price_source = excluded.price_source
        """,
        (symbol, label, envelope, currency, price_source),
    )


def set_manual_value(symbol: str, value: float) -> None:
    execute("UPDATE asset SET manual_value = ? WHERE symbol = ?", (value, symbol))


def set_actual_quantity(symbol: str, quantity: float | None) -> None:
    execute("UPDATE asset SET actual_quantity = ? WHERE symbol = ?", (quantity, symbol))


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
