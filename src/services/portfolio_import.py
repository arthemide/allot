"""Turn a broker snapshot into opening positions.

Shared by the CSV import and the connector sync. A snapshot is a point in
time, never a history: each line sets the asset's opening position to what the
broker reports, PRUM included, so importing again replaces rather than adds.

`authoritative` is the difference between the two callers. The CSV import
trusts only the rows it was handed: it leaves everything else alone, and
manual transactions still stack on top. A connector sync speaks for the whole
account, so it also clears the manual transactions of the assets it touches
and zeroes any asset of the envelope the broker no longer reports.

No network beyond the ticker search, no HTTP: rows in, a report dict out.
"""

from __future__ import annotations

from typing import Protocol

from src.databases import sqlite as db
from src.services import prices


class SnapshotLine(Protocol):
    """What a broker reports for one holding, whatever the source."""

    isin: str
    name: str
    quantity: float
    prum: float


def apply_snapshot(
    envelope: str, lines: list[SnapshotLine], *, authoritative: bool = False
) -> dict:
    """Write the lines as opening positions; return an ImportReport dict."""
    if db.get_envelope(envelope) is None:
        db.upsert_envelope(envelope, 0.0)

    imported, unresolved, elsewhere = [], [], []
    touched: set[str] = set()
    for row in lines:
        hits = prices.search(row.isin, limit=1)
        if not hits:
            unresolved.append({"isin": row.isin, "name": row.name})
            continue
        hit = hits[0]
        symbol = hit["symbol"]
        existing = db.get_asset(symbol)
        if existing is None:
            db.add_asset(symbol, row.name, envelope, hit.get("currency") or "EUR")
        elif existing["envelope"] != envelope:
            if authoritative:
                # The broker says this line is in `envelope`; move it there,
                # keeping the user's label and weight. Otherwise a later
                # account's zero-out would wrongly drop it.
                db.update_asset(symbol, existing["label"], envelope, existing["weight"])
            else:
                # Left where the user filed it; the position is updated below.
                elsewhere.append(
                    {
                        "symbol": symbol,
                        "isin": row.isin,
                        "label": row.name,
                        "envelope": existing["envelope"],
                    }
                )
        db.set_opening_position(symbol, row.quantity, row.prum * row.quantity)
        touched.add(symbol)
        if authoritative:
            # The broker's position is the whole truth; manual trades would
            # double-count on top of it.
            db.delete_transactions_of(symbol)
        imported.append(
            {
                "symbol": symbol,
                "isin": row.isin,
                "label": row.name,
                "quantity": row.quantity,
                "prum": row.prum,
            }
        )

    if authoritative:
        _zero_sold(envelope, touched)

    return {
        "imported": imported,
        "unresolved": unresolved,
        "elsewhere": elsewhere,
        "total": len(lines),
    }


def _zero_sold(envelope: str, touched: set[str]) -> None:
    """An asset of the envelope the broker no longer reports was sold off."""
    for asset in db.all_assets():
        if asset["envelope"] != envelope or asset["symbol"] in touched:
            continue
        db.set_opening_position(asset["symbol"], 0, None)
        db.delete_transactions_of(asset["symbol"])
