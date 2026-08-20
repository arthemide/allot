"""Load the CSV export of the old Postgres database into SQLite.

Idempotent and replayable: assets are keyed by symbol, transactions by their
broker order id, so running it twice changes nothing.

    uv run migrate.py --csv-dir ../migration-csv

The old schema maps onto the new one like this:

    funds                -> asset.envelope (via FUND_TO_ENVELOPE)
    stocks               -> asset
    stocks.shares_number -> asset.base_quantity   (opening position)
    stocks.base_prum     -> asset.base_prum, or cost / shares_number when the
                            old row had no base_prum and no transactions
    asset_transactions   -> transaction

Dropped on purpose: current_repartition, target_repartition,
arbitration_threshold and threshold_to_alert. Allocation now lives in
config.toml. alembic_version is not migrated.
"""

from __future__ import annotations

import argparse
import csv
import sqlite3
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).parent
DEFAULT_DB = ROOT / "wealth.db"
DEFAULT_CSV_DIR = ROOT.parent / "migration-csv"

# Old fund names to new envelope names.
FUND_TO_ENVELOPE = {
    "Binance": "CRYPTO",
    "PEA - Bourso": "PEA",
    "Titre - Bourso": "CTO",
    "AFER": "AFER",
}


def _read_csv(csv_dir: Path, name: str) -> list[dict]:
    path = csv_dir / f"{name}.csv"
    if not path.exists():
        sys.exit(f"missing CSV: {path}")
    with path.open(encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _number(raw: str | None) -> float | None:
    if raw is None or raw == "":
        return None
    return float(raw)


def create_schema(connection: sqlite3.Connection) -> None:
    connection.executescript((ROOT / "schema.sql").read_text(encoding="utf-8"))


def load_config(path: Path) -> dict:
    with path.open("rb") as handle:
        return tomllib.load(handle)


def migrate_assets(
    connection: sqlite3.Connection, csv_dir: Path, config: dict
) -> tuple[int, int]:
    """Insert one asset row per old stock, then fill in config-only assets."""
    funds = {row["id"]: row["name"] for row in _read_csv(csv_dir, "funds")}
    stocks = _read_csv(csv_dir, "stocks")

    migrated = 0
    for stock in stocks:
        fund_name = funds.get(stock["fund_id"], "")
        envelope = FUND_TO_ENVELOPE.get(fund_name)
        if envelope is None:
            sys.exit(
                f"no envelope mapped for fund {fund_name!r} "
                f"(symbol {stock['symbol']}); add it to FUND_TO_ENVELOPE"
            )

        base_quantity = _number(stock["shares_number"]) or 0.0
        base_prum = _number(stock["base_prum"])
        if base_prum is None and base_quantity > 0:
            # No base_prum: the old row carried the whole position in
            # shares_number / cost, with no transaction behind it.
            cost = _number(stock["cost"]) or 0.0
            base_prum = cost / base_quantity if cost > 0 else None
        if base_prum is None:
            base_quantity = 0.0

        connection.execute(
            """
            INSERT INTO asset (symbol, label, envelope, currency, price_source,
                               base_quantity, base_prum)
            VALUES (?, ?, ?, ?, 'yfinance', ?, ?)
            ON CONFLICT(symbol) DO UPDATE SET
                label = excluded.label,
                envelope = excluded.envelope,
                currency = excluded.currency,
                base_quantity = excluded.base_quantity,
                base_prum = excluded.base_prum
            """,
            (
                stock["symbol"],
                stock["name"],
                envelope,
                stock.get("currency") or "EUR",
                base_quantity,
                base_prum,
            ),
        )
        migrated += 1

    # Assets that exist only in config.toml get an empty row, so every
    # configured envelope has something to show.
    filled = 0
    for entry in config.get("assets", []):
        symbol = entry["ticker"]
        existing = connection.execute(
            "SELECT 1 FROM asset WHERE symbol = ?", (symbol,)
        ).fetchone()
        if existing:
            continue
        connection.execute(
            """
            INSERT INTO asset (symbol, label, envelope, currency, price_source,
                               base_quantity, base_prum)
            VALUES (?, ?, ?, ?, ?, 0, NULL)
            """,
            (
                symbol,
                entry.get("label", symbol),
                entry["envelope"],
                entry["currency"],
                entry.get("price_source", "yfinance"),
            ),
        )
        filled += 1

    return migrated, filled


def migrate_transactions(connection: sqlite3.Connection, csv_dir: Path) -> int:
    """Copy asset_transactions across, deriving fees from total_cost."""
    stocks = {row["id"]: row["symbol"] for row in _read_csv(csv_dir, "stocks")}
    rows = _read_csv(csv_dir, "asset_transactions")

    for row in rows:
        symbol = stocks.get(row["asset_id"])
        if symbol is None:
            sys.exit(
                f"transaction {row['id']} points at unknown asset_id "
                f"{row['asset_id']}: refusing to drop it silently"
            )

        quantity = float(row["quantity"])
        unit_price = float(row["price"])
        total_cost = float(row["total_cost"])
        # The old schema never stored fees separately. total_cost is expected to
        # equal quantity * price; anything left over is treated as fees rather
        # than invented or discarded.
        fees = max(0.0, total_cost - quantity * unit_price)

        external_id = row["order_id"] or None
        if external_id is None:
            # No broker reference to dedupe on: fall back to the full tuple so
            # a replay does not duplicate the row.
            already = connection.execute(
                """
                SELECT 1 FROM "transaction"
                WHERE symbol = ? AND date = ? AND side = ?
                  AND quantity = ? AND unit_price = ?
                """,
                (symbol, row["timestamp"], row["transaction_type"], quantity,
                 unit_price),
            ).fetchone()
            if already:
                continue

        connection.execute(
            """
            INSERT INTO "transaction"
                (symbol, date, side, quantity, unit_price, fees, external_id)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(external_id) DO NOTHING
            """,
            (symbol, row["timestamp"], row["transaction_type"], quantity,
             unit_price, fees, external_id),
        )

    return len(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--csv-dir", type=Path, default=DEFAULT_CSV_DIR)
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--config", type=Path, default=ROOT / "config.toml")
    args = parser.parse_args()

    config = load_config(args.config)

    connection = sqlite3.connect(args.db)
    connection.execute("PRAGMA foreign_keys = ON")
    try:
        create_schema(connection)
        migrated, filled = migrate_assets(connection, args.csv_dir, config)
        transactions = migrate_transactions(connection, args.csv_dir)
        connection.commit()
    finally:
        connection.close()

    print(f"assets migrated from Postgres : {migrated}")
    print(f"assets created from config    : {filled}")
    print(f"transactions read             : {transactions}")
    print(f"database                      : {args.db}")


if __name__ == "__main__":
    main()
