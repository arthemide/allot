"""A bank sync, from the lines the bank reported to the positions Allot derives.

Each bank account syncs into the envelope the user placed it in, once, the
first time the account shows up. Nothing is ever filed under an envelope
named after whatever label the bank happens to use: an account nobody placed
yet stops the sync until it is, and an account left out (no envelope) is
skipped from then on.

Accounts placed in the same envelope are applied together, so that one of
them never zeroes what the other holds.
"""

from __future__ import annotations

from typing import Iterable

from src.databases import sqlite as db
from src.models.schema import PositionRow, SnapshotLine
from src.services import portfolio_import


def by_account(rows: Iterable[PositionRow]) -> dict[str, list[SnapshotLine]]:
    """The security lines of each account, cash-only accounts included.

    A cash balance is not an asset, and a line without a quantity cannot hold
    a position. Everything else is kept, even without an ISIN or a cost
    basis: those come back unresolved rather than silently dropped. An
    account holding only cash is kept too, empty: it still says that
    everything it held was sold.
    """
    accounts: dict[str, list[SnapshotLine]] = {}
    for row in rows:
        lines = accounts.setdefault(row.account, [])
        if row.support_type == "cash" or not row.quantity:
            continue
        lines.append(
            SnapshotLine(
                isin=row.isin,
                name=row.label,
                quantity=row.quantity,
                prum=row.unit_cost,
                currency=row.currency,
            )
        )
    return accounts


def new_accounts(rows: Iterable[PositionRow]) -> list[dict]:
    """The accounts no envelope was chosen for yet, with a default to offer."""
    placed = db.bank_accounts()
    envelopes = {
        envelope["name"].upper(): envelope["name"] for envelope in db.all_envelopes()
    }
    return [
        {
            "account": account,
            "lines": len(lines),
            "envelope": envelopes.get(account.upper()),
        }
        for account, lines in by_account(rows).items()
        if account not in placed
    ]


def place(envelopes: dict[str, str | None], rows: Iterable[PositionRow]) -> None:
    """Record where each new account syncs; every one of them needs an answer.

    An empty answer, or None, leaves the account out. An
    envelope that does not exist yet is created, as adding an asset would.
    """
    missing = [
        account["account"]
        for account in new_accounts(rows)
        if account["account"] not in envelopes
    ]
    if missing:
        raise ValueError(f"No envelope chosen for {', '.join(missing)}.")
    for account, envelope in envelopes.items():
        name = (envelope or "").strip() or None
        if name is not None and db.get_envelope(name) is None:
            db.upsert_envelope(name, 0.0)
        db.set_bank_account(account, name)


def apply(rows: Iterable[PositionRow]) -> dict:
    """Sync every placed account into its envelope; return one ImportReport dict."""
    placed = db.bank_accounts()
    by_envelope: dict[str, list[SnapshotLine]] = {}
    for account, lines in by_account(rows).items():
        envelope = placed.get(account)
        if envelope is None:
            # Left out by the user, or not placed yet (new_accounts says so).
            continue
        by_envelope.setdefault(envelope, []).extend(lines)

    merged = {
        "imported": [],
        "unresolved": [],
        "elsewhere": [],
        "conflicts": [],
        "total": 0,
    }
    for envelope, lines in by_envelope.items():
        report = portfolio_import.apply_snapshot(envelope, lines, authoritative=True)
        for key in ("imported", "unresolved", "elsewhere", "conflicts"):
            merged[key].extend(report[key])
        merged["total"] += report["total"]
    return merged
