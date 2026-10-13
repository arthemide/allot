"""Turn a broker snapshot into opening positions.

Shared by the CSV import and the connector sync. A snapshot is a point in
time, never a history.

`authoritative` is the difference between the two callers. The CSV import
trusts only the rows it was handed: each one sets the asset's opening
position to what the broker reports, manual transactions still stack on top,
and everything else is left alone. A connector sync speaks for the whole
account: it makes every asset it reports hold exactly what the bank says,
and zeroes any asset of the envelope the bank no longer reports.

It does so without touching a single transaction - they are the history the
envelope's cash is derived from. The opening position absorbs the difference
instead (calc.opening_for); when it cannot, because the trades already hold
more than the bank reports, the line is reported as a conflict and left
alone.

No network beyond the ticker search, no HTTP: rows in, a report dict out.
"""

from __future__ import annotations

from typing import Protocol

from src import calc
from src.databases import sqlite as db
from src.services import portfolio, prices


class SnapshotLine(Protocol):
    """What a broker reports for one holding, whatever the source.

    `isin` and `prum` are optional because a connector reads lines the broker
    does not tag or price (a CEFP line by parts): those are reported
    unresolved, never guessed. `currency`, when known, is what the Yahoo
    listing must be quoted in.
    """

    isin: str | None
    name: str
    quantity: float
    prum: float | None


def apply_snapshot(
    envelope: str, lines: list[SnapshotLine], *, authoritative: bool = False
) -> dict:
    """Write the lines as opening positions; return an ImportReport dict."""
    if db.get_envelope(envelope) is None:
        db.upsert_envelope(envelope, 0.0)

    imported, unresolved, elsewhere, conflicts = [], [], [], []
    touched: set[str] = set()
    for row in lines:
        hit = _resolve(row)
        if hit is None or row.prum is None:
            unresolved.append({"isin": row.isin, "name": row.name})
            continue
        symbol = hit["symbol"]
        existing = db.get_asset(symbol)
        if existing is None:
            db.add_asset(symbol, row.name, envelope, hit.get("currency") or "EUR")
        elif existing["envelope"] != envelope and authoritative:
            # The broker says this line is in `envelope`; move it there,
            # keeping the user's label and weight. Otherwise a later
            # account's zero-out would wrongly drop it.
            db.update_asset(symbol, existing["label"], envelope, existing["weight"])
        elif existing["envelope"] != envelope:
            # Left where the user filed it; the position is updated below.
            elsewhere.append(
                {
                    "symbol": symbol,
                    "isin": row.isin,
                    "label": row.name,
                    "envelope": existing["envelope"],
                }
            )
        touched.add(symbol)
        if authoritative:
            conflict = _reconcile(symbol, row.name, row.quantity, row.prum)
            if conflict is not None:
                conflicts.append(conflict)
                continue
        else:
            db.set_opening_position(symbol, row.quantity, row.prum * row.quantity)
        imported.append(
            {
                "symbol": symbol,
                "isin": row.isin,
                "label": row.name,
                "quantity": row.quantity,
                "prum": row.prum,
            }
        )

    # An unresolved line may still be held. Never mark anything sold until
    # every broker row was matched to a ticker in its own currency.
    if authoritative and not unresolved:
        conflicts.extend(_zero_sold(envelope, touched))

    return {
        "imported": imported,
        "unresolved": unresolved,
        "elsewhere": elsewhere,
        "conflicts": conflicts,
        "total": len(lines),
    }


def _resolve(row: SnapshotLine) -> dict | None:
    """The Yahoo listing of the line's ISIN, in the broker's currency if known."""
    if not row.isin:
        # No identifier to search with: never guess from a label.
        return None
    currency = getattr(row, "currency", None)
    currency = str(currency).upper() if currency else None
    # Each hit costs a quote lookup: without a currency to filter on, the
    # first one is the answer (what the CSV import has always taken).
    for hit in prices.search(row.isin, limit=10 if currency else 1):
        if currency is None or str(hit.get("currency") or "").upper() == currency:
            return hit
    return None


def _reconcile(
    symbol: str, label: str, quantity: float, prum: float | None
) -> dict | None:
    """Make the asset hold `quantity` at `prum`; return a conflict if it cannot."""
    trades = portfolio.trades_of(symbol)
    opening = calc.opening_for(trades, quantity, prum)
    if opening is None:
        return {
            "symbol": symbol,
            "label": label,
            "bank_quantity": quantity,
            "tracked_quantity": calc.position(trades).quantity,
        }
    base_quantity, base_prum = opening
    db.set_opening_position(
        symbol, base_quantity, base_quantity * base_prum if base_prum else None
    )
    return None


def _zero_sold(envelope: str, touched: set[str]) -> list[dict]:
    """An asset of the envelope the broker no longer reports was sold off."""
    conflicts = []
    for asset in db.all_assets():
        if asset["envelope"] != envelope or asset["symbol"] in touched:
            continue
        held = calc.position(
            portfolio.trades_of(asset["symbol"]),
            asset["base_quantity"],
            asset["base_prum"],
        )
        if held.quantity <= calc.QUANTITY_TOLERANCE:
            continue
        # Sold at the PRUM it had: a sell never moves the PRUM.
        conflict = _reconcile(asset["symbol"], asset["label"], 0.0, held.prum)
        if conflict is not None:
            conflicts.append(conflict)
    return conflicts
