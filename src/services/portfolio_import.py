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
    """What a broker reports for one holding, whatever the source.

    `broker_key` is the stable identity of the line; `isin` is optional because
    a part-based line the broker does not tag (a CEFP line without ISIN) still
    has to be importable once the user has picked a ticker for it.
    """

    broker_key: str
    isin: str | None
    name: str
    quantity: float
    prum: float | None
    currency: str | None


def apply_snapshot(
    envelope: str,
    lines: list[SnapshotLine],
    *,
    authoritative: bool = False,
    reconcile_missing: bool | None = None,
    symbols: dict[str, str] | None = None,
) -> dict:
    """Write the lines as opening positions; return an ImportReport dict.

    A line already linked to a Yahoo ticker (by its `broker_key`) is updated in
    place, so a manual choice is remembered across syncs. An unlinked line with
    an ISIN is looked up automatically and must match the broker's currency. An
    unlinked line without an ISIN is never guessed: it is reported unresolved
    so the user can pick the ticker by hand. ``symbols`` carries an explicit,
    user-selected ticker for such a line, keyed by ``broker_key``.
    """
    if db.get_envelope(envelope) is None:
        db.upsert_envelope(envelope, 0.0)

    reconcile_missing = (
        authoritative if reconcile_missing is None else reconcile_missing
    )
    imported, unresolved, elsewhere = [], [], []
    touched: set[str] = set()
    for row in lines:
        currency = _currency(row)
        broker_key = _broker_key(row)
        linked = db.get_asset_by_broker_key(broker_key)
        if row.prum is None:
            # No cost basis from the bank. The PRUM the user gave earlier still
            # holds while the number of parts is unchanged; once it moves, a
            # new amount invested is needed.
            if linked is not None and linked["base_quantity"] == row.quantity:
                touched.add(linked["symbol"])
                imported.append(
                    {
                        "symbol": linked["symbol"],
                        "isin": row.isin,
                        "label": row.name,
                        "quantity": row.quantity,
                        "prum": linked["base_prum"],
                    }
                )
                continue
            unresolved.append(_unresolved(row, currency))
            continue
        requested = (symbols or {}).get(broker_key)
        hit = None
        if linked is not None and requested in (None, linked["symbol"]):
            if currency and linked["currency"] != currency:
                # Linked earlier (a manual add with its ISIN, say) but quoted
                # in another currency: the PRUM would not compare.
                unresolved.append(_unresolved(row, currency))
                continue
            symbol = linked["symbol"]
            existing = linked
        else:
            hit = _resolve_hit(row, currency, symbols or {})
            if hit is None:
                unresolved.append(_unresolved(row, currency))
                continue
            symbol = hit["symbol"]
            if linked is not None and linked["symbol"] != symbol:
                # The user moved this line to another ticker. The key is
                # unique, so unlink the old asset, and stop it from still
                # holding the position the broker now reports elsewhere.
                db.set_asset_broker_key(linked["symbol"], None)
                if authoritative:
                    db.set_opening_position(linked["symbol"], 0, None)
                    db.delete_transactions_of(linked["symbol"])
            existing = db.get_asset(symbol)

        if existing is None:
            db.add_asset(
                symbol, row.name, envelope, (hit or {}).get("currency") or "EUR"
            )
        else:
            if hit is not None and hit.get("currency"):
                db.set_asset_currency(symbol, hit["currency"])
            if existing["envelope"] != envelope and authoritative:
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
        db.set_asset_broker_key(symbol, broker_key)
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

    # An unresolved line may still be held. Never mark anything sold until
    # every broker row was matched to a ticker in its own currency.
    if reconcile_missing and not unresolved:
        _zero_sold(envelope, touched)

    return {
        "imported": imported,
        "unresolved": unresolved,
        "elsewhere": elsewhere,
        "total": len(lines),
    }


def _currency(row: SnapshotLine) -> str | None:
    value = getattr(row, "currency", None)
    return str(value).upper() if value else None


def _broker_key(row: SnapshotLine) -> str:
    key = getattr(row, "broker_key", None)
    if key:
        return key
    return str(getattr(row, "isin") or getattr(row, "name") or "")


def _resolve_hit(row: SnapshotLine, currency: str | None, symbols: dict) -> dict | None:
    """Pick the Yahoo listing for an unlinked line, or None for the user to pick."""
    requested = symbols.get(_broker_key(row))
    if requested is not None:
        hits = prices.search(requested, limit=10)
        return next(
            (h for h in hits if h["symbol"] == requested and _currency_ok(h, currency)),
            None,
        )
    isin = getattr(row, "isin", None)
    if not isin:
        # No broker identifier to search with: never guess, hand it to the user.
        return None
    hits = prices.search(isin, limit=10)
    return next((h for h in hits if _currency_ok(h, currency)), None)


def _currency_ok(hit: dict, currency: str | None) -> bool:
    if currency is None:
        return True
    return str(hit.get("currency") or "").upper() == currency


def _unresolved(row: SnapshotLine, currency: str | None) -> dict:
    line = {
        "broker_key": _broker_key(row),
        "isin": getattr(row, "isin", None),
        "name": row.name,
    }
    account = getattr(row, "account", None)
    if account is not None:
        line.update(
            account=account,
            currency=currency,
            quantity=row.quantity,
            prum=row.prum,
        )
    return line


def _zero_sold(envelope: str, touched: set[str]) -> None:
    """An asset of the envelope the broker no longer reports was sold off."""
    for asset in db.all_assets():
        if asset["envelope"] != envelope or asset["symbol"] in touched:
            continue
        db.set_opening_position(asset["symbol"], 0, None)
        db.delete_transactions_of(asset["symbol"])
