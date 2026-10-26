"""A source sync, from the lines a source reported to the positions Allot derives.

Every source goes through here, read on the server (BoursoBank, through woob)
or in the browser (Afer, through a bookmarklet). The reading is the source's
job; this module only knows rows.

Each account syncs into the envelope the user placed it in, once, the first
time the account shows up. Nothing is ever filed under an envelope named after
whatever label the source happens to use: an account nobody placed yet stops
the sync until it is, and an account left out (no envelope) is skipped from
then on. A line without an ISIN is mapped to its ticker by hand the same way,
once; mapped to nothing, it is left out.

Accounts placed in the same envelope are applied together, so that one of
them never zeroes what the other holds. How far a sync zeroes is the source's
`owns_envelope` (src/sources/registry.py).
"""

from __future__ import annotations

import re
import unicodedata
from typing import Iterable

from src.databases import sqlite as db
from src.models.schema import (
    AccountChoice,
    AccountPlacement,
    LineMapping,
    PendingChoices,
    PendingLine,
    PositionRow,
    SnapshotLine,
    SourceSnapshot,
)
from src.services import portfolio_import
from src.sources import registry


def rows_from_snapshot(snapshot: SourceSnapshot) -> list[PositionRow]:
    """Turn a browser source's snapshot into the rows a server source reads."""
    rows: list[PositionRow] = []
    for account in snapshot.accounts:
        for line in account.lines:
            unit_cost = line.unit_cost
            if unit_cost is None and line.invested is not None and line.quantity:
                unit_cost = line.invested / line.quantity
            rows.append(
                PositionRow(
                    source=snapshot.source,
                    account=account.label,
                    # No quantity: an amount, not units - the euro fund of an
                    # assurance vie. Reported as available, never a position.
                    support_type="cash" if line.quantity is None else "security",
                    isin=line.isin,
                    label=line.label,
                    quantity=line.quantity,
                    value=line.valuation or 0.0,
                    currency=line.currency or "EUR",
                    unit_cost=unit_cost,
                    unit_price=line.unit_value,
                    by_amount=line.by_amount,
                )
            )
    return rows


def _is_amount(row: PositionRow) -> bool:
    """A cash balance, or a line without units: it cannot hold a position."""
    return row.support_type == "cash" or not row.quantity


def by_account(
    source: str, rows: Iterable[PositionRow]
) -> dict[str, list[SnapshotLine]]:
    """The security lines of each account, cash-only accounts included.

    Everything that holds units is kept, even without an ISIN or a cost basis:
    those come back unresolved rather than silently dropped, unless the user
    left the line out. An account holding only cash is kept too, empty: it
    still says that everything it held was sold.
    """
    mapping = db.source_lines(source)
    accounts: dict[str, list[SnapshotLine]] = {}
    for row in rows:
        lines = accounts.setdefault(row.account, [])
        if _is_amount(row):
            continue
        symbol = mapping.get(row.label)  # None means left out, missing means unknown
        if symbol is None and row.label in mapping:
            continue
        lines.append(
            SnapshotLine(
                isin=row.isin,
                name=row.label,
                quantity=row.quantity,
                prum=row.unit_cost,
                currency=row.currency,
                symbol=symbol,
                by_amount=row.by_amount,
            )
        )
    return accounts


def pending(source: str, rows: Iterable[PositionRow]) -> PendingChoices:
    """What still needs a choice before the sync can run.

    The accounts never placed, with an envelope of the same name to offer, and
    the lines without an ISIN never mapped, with a guess among the assets.
    """
    rows = list(rows)
    placed = db.source_accounts(source)
    mapped = db.source_lines(source)
    envelopes = {e["name"].upper(): e["name"] for e in db.all_envelopes()}
    assets = db.all_assets()
    accounts: list[AccountChoice] = []
    lines: dict[str, PendingLine] = {}
    for account, snapshot_lines in by_account(source, rows).items():
        if account not in placed:
            accounts.append(
                AccountChoice(
                    account=account,
                    lines=len(snapshot_lines),
                    envelope=envelopes.get(account.upper()),
                )
            )
        elif placed[account] is None:
            continue  # Left out: none of its lines matter.
        for line in snapshot_lines:
            if line.isin or line.name in mapped or line.name in lines:
                continue
            lines[line.name] = PendingLine(
                account=account,
                label=line.name,
                symbol=_suggest_asset(line.name, assets),
            )
    return PendingChoices(accounts=accounts, lines=list(lines.values()))


def _suggest_asset(label: str, assets: list[dict]) -> str | None:
    """The asset whose label shares the most words with the line's. A guess."""
    words = _words(label)
    best, best_score = None, 0
    for asset in assets:
        score = len(words & _words(asset["label"]))
        if score > best_score:
            best, best_score = asset["symbol"], score
    return best


def _words(value: str) -> set[str]:
    normalised = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    return {w for w in re.split(r"[^a-z0-9]+", normalised.lower()) if len(w) > 2}


def place(
    source: str,
    placements: list[AccountPlacement],
    mappings: list[LineMapping],
    rows: Iterable[PositionRow],
) -> None:
    """Remember the user's choices. Refuses, writing nothing, if an account is left.

    An empty answer, or None, leaves the account or the line out. An envelope
    that does not exist yet is created, as adding an asset would.
    """
    envelopes = {p.account: _blank_to_none(p.envelope) for p in placements}
    symbols = {m.label: _blank_to_none(m.symbol) for m in mappings}
    missing = [
        a.account for a in pending(source, rows).accounts if a.account not in envelopes
    ]
    if missing:
        raise ValueError(f"No envelope chosen for {', '.join(missing)}.")
    for account, envelope in envelopes.items():
        if envelope is not None and db.get_envelope(envelope) is None:
            db.upsert_envelope(envelope, 0.0)
        db.set_source_account(source, account, envelope)
    for label, symbol in symbols.items():
        db.set_source_line(source, label, symbol)


def _blank_to_none(value: str | None) -> str | None:
    """A choice typed as spaces is no choice: the account or line is left out."""
    return (value or "").strip() or None


def apply(source: str, rows: Iterable[PositionRow]) -> dict:
    """Sync every placed account into its envelope; return one ImportReport dict.

    A source that owns its envelopes zeroes whatever of the envelope it no
    longer reports. One that does not only zeroes the assets its lines map to:
    another asset of the envelope, tracked by hand or by another source, is
    left alone.
    """
    rows = list(rows)
    placed = db.source_accounts(source)
    scope = (
        None
        if registry.get(source).owns_envelope
        else {symbol for symbol in db.source_lines(source).values() if symbol}
    )

    by_envelope: dict[str, list[SnapshotLine]] = {}
    for account, lines in by_account(source, rows).items():
        envelope = placed.get(account)
        if envelope is None:
            # Left out by the user, or not placed yet (pending says so).
            continue
        by_envelope.setdefault(envelope, []).extend(lines)

    merged = {
        "imported": [],
        "unresolved": [],
        "elsewhere": [],
        "conflicts": [],
        "available": _available(rows, placed),
        "total": 0,
    }
    for envelope, lines in by_envelope.items():
        report = portfolio_import.apply_snapshot(
            envelope, lines, authoritative=True, scope=scope
        )
        for key in ("imported", "unresolved", "elsewhere", "conflicts"):
            merged[key].extend(report[key])
        merged["total"] += report["total"]
    return merged


def _available(rows: list[PositionRow], placed: dict[str, str | None]) -> list[dict]:
    """The amounts of the placed accounts that hold no units. Shown, not written."""
    return [
        {
            "account": row.account,
            "envelope": placed[row.account],
            "label": row.label,
            "value": row.value,
            "currency": row.currency,
        }
        for row in rows
        if _is_amount(row) and row.value and placed.get(row.account) is not None
    ]
