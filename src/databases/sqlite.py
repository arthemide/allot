"""SQLite access. Standard library only, no ORM.

Every read returns plain dicts; no derived state is ever stored,
so there is nothing to keep in sync.
"""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path
from typing import Any, Iterator

from src import calc

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
        # One transaction for the upgrades: sqlite3 would commit the ALTER on
        # its own, and a crash before the seeding would leave it half done.
        connection.execute("BEGIN")
        _add_by_amount(connection)
        _merge_bank_accounts(connection)
        connection.commit()
    finally:
        connection.close()


def _merge_bank_accounts(connection: sqlite3.Connection) -> None:
    """Move the BoursoBank placements of an older database into source_account.

    They used to have their own table; every source now shares one, keyed by
    the source. An account already placed there keeps its newer choice.
    """
    tables = {
        row["name"]
        for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'"
        )
    }
    if "bank_account" not in tables:
        return
    connection.execute(
        "INSERT OR IGNORE INTO source_account (source, account, envelope) "
        "SELECT 'bourso', account, envelope FROM bank_account"
    )
    connection.execute("DROP TABLE bank_account")


def _add_by_amount(connection: sqlite3.Connection) -> None:
    """Add `asset.by_amount` to a database that predates it.

    SQLite only adds columns explicitly, unlike CREATE TABLE IF NOT EXISTS.
    Existing assets are seeded with the rule the flag replaces, so the monthly
    split does not change on upgrade: crypto pairs and anything already
    traded in fractions keep being bought by the amount.
    """
    columns = {row["name"] for row in connection.execute("PRAGMA table_info(asset)")}
    if "by_amount" in columns:
        return
    connection.execute(
        "ALTER TABLE asset ADD COLUMN by_amount INTEGER NOT NULL DEFAULT 0 "
        "CHECK (by_amount IN (0, 1))"
    )
    in_fractions = {
        row["symbol"]
        for row in connection.execute(
            'SELECT DISTINCT symbol FROM "transaction" '
            "WHERE quantity <> CAST(quantity AS INTEGER)"
        )
    }
    seeded = [
        (row["symbol"],)
        for row in connection.execute("SELECT symbol FROM asset")
        if calc.bought_by_amount(row["symbol"], row["symbol"] in in_fractions)
    ]
    connection.executemany("UPDATE asset SET by_amount = 1 WHERE symbol = ?", seeded)


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
    symbol: str,
    label: str,
    envelope: str,
    currency: str,
    weight: float = 1.0,
    by_amount: bool = False,
) -> None:
    execute(
        """
        INSERT INTO asset (symbol, label, envelope, currency, weight, by_amount)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(symbol) DO UPDATE SET
            label = excluded.label,
            envelope = excluded.envelope,
            currency = excluded.currency,
            weight = excluded.weight,
            by_amount = excluded.by_amount
        """,
        (symbol, label, envelope, currency, weight, int(by_amount)),
    )


def update_asset(
    symbol: str,
    label: str,
    envelope: str,
    weight: float,
    by_amount: bool | None = None,
) -> None:
    """Rewrite the user's settings; `by_amount=None` leaves the flag alone."""
    execute(
        "UPDATE asset SET label = ?, envelope = ?, weight = ?, "
        "by_amount = COALESCE(?, by_amount) WHERE symbol = ?",
        (
            label,
            envelope,
            weight,
            None if by_amount is None else int(by_amount),
            symbol,
        ),
    )


def set_by_amount(symbol: str, by_amount: bool) -> None:
    execute("UPDATE asset SET by_amount = ? WHERE symbol = ?", (int(by_amount), symbol))


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
    """Transactions go with it, through ON DELETE CASCADE.

    So do the source lines mapped to it: `source_line.symbol` cannot be a
    foreign key, the ticker being picked before its asset exists.
    """
    connection = connect()
    try:
        connection.execute("DELETE FROM source_line WHERE symbol = ?", (symbol,))
        connection.execute("DELETE FROM asset WHERE symbol = ?", (symbol,))
        connection.commit()
    finally:
        connection.close()


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


def get_envelope_start(name: str) -> dict[str, Any] | None:
    """Where the envelope's strategy starts, or None when it tracks no cash."""
    rows = query("SELECT * FROM envelope_start WHERE envelope = ?", (name,))
    return rows[0] if rows else None


def set_envelope_start(name: str, started_on: str, opening_cash: float) -> None:
    execute(
        """
        INSERT INTO envelope_start (envelope, started_on, opening_cash)
        VALUES (?, ?, ?)
        ON CONFLICT(envelope) DO UPDATE SET
            started_on = excluded.started_on,
            opening_cash = excluded.opening_cash
        """,
        (name, started_on, opening_cash),
    )


def clear_envelope_start(name: str) -> None:
    execute("DELETE FROM envelope_start WHERE envelope = ?", (name,))


def envelope_transactions(name: str, since: str) -> list[dict[str, Any]]:
    """Every trade on the envelope's assets from `since` on, oldest first.

    Inclusive: a trade entered the day a start is recorded happened after the
    cash was counted, so it still has to be subtracted.
    """
    return query(
        """
        SELECT t.*, a.currency FROM "transaction" t
        JOIN asset a ON a.symbol = t.symbol
        WHERE a.envelope = ? AND t.date >= ?
        ORDER BY t.date, t.id
        """,
        (name, since),
    )


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


# --- sources -----------------------------------------------------------------


def source_accounts(source: str) -> dict[str, str | None]:
    """Each account already placed for `source`, and the envelope it syncs into."""
    return {
        row["account"]: row["envelope"]
        for row in query(
            "SELECT account, envelope FROM source_account WHERE source = ?", (source,)
        )
    }


def set_source_account(source: str, account: str, envelope: str | None) -> None:
    """Place an account of `source` in an envelope, or leave it out with None."""
    execute(
        """
        INSERT INTO source_account (source, account, envelope)
        VALUES (?, ?, ?)
        ON CONFLICT(source, account) DO UPDATE SET envelope = excluded.envelope
        """,
        (source, account, envelope),
    )


def envelope_sources(envelope: str) -> list[dict[str, Any]]:
    """The accounts, of any source, that sync into `envelope`."""
    return query(
        "SELECT source, account FROM source_account WHERE envelope = ? "
        "ORDER BY source, account",
        (envelope,),
    )


def source_lines(source: str) -> dict[str, str | None]:
    """Each label already mapped for `source`, to a ticker or to None (left out)."""
    return {
        row["label"]: row["symbol"]
        for row in query(
            "SELECT label, symbol FROM source_line WHERE source = ?", (source,)
        )
    }


def set_source_line(source: str, label: str, symbol: str | None) -> None:
    """Remember which ticker a line of `source` maps to, or None to leave it out."""
    execute(
        """
        INSERT INTO source_line (source, label, symbol) VALUES (?, ?, ?)
        ON CONFLICT(source, label) DO UPDATE SET symbol = excluded.symbol
        """,
        (source, label, symbol),
    )


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
