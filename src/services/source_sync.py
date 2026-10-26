"""A source sync, from the lines a source reported to the positions Allot derives.

Same shape as bank_sync, but multi-source: each source has its own remembered
accounts and line-to-ticker mappings. The reading itself is the source's job.
"""

from __future__ import annotations

from typing import Iterable

from src.databases import sqlite as db
from src.models.schema import (
    AccountPlacement,
    LineMapping,
    PendingAccount,
    PendingChoices,
    PendingLine,
    PositionRow,
    SnapshotLine,
    SourceSnapshot,
)
from src.services import portfolio_import


def rows_from_snapshot(snapshot: SourceSnapshot) -> list[PositionRow]:
    """Turn a source snapshot into the position rows the sync works on."""
    rows: list[PositionRow] = []
    for account in snapshot.accounts:
        for line in account.lines:
            unit_cost = line.unit_cost
            if unit_cost is None and line.invested is not None and line.quantity:
                unit_cost = line.invested / line.quantity
            if line.quantity is None:
                # No quantity: cash or a fund bought by the amount only.
                # The euro fund of an assurance vie lands here and is ignored.
                support = "cash"
            else:
                support = "security"
            rows.append(
                PositionRow(
                    source=snapshot.source,
                    account=account.label,
                    support_type=support,
                    isin=line.isin,
                    label=line.label,
                    quantity=line.quantity,
                    value=line.valuation or 0.0,
                    currency=line.currency or "EUR",
                    unit_cost=unit_cost,
                    unit_price=line.unit_value,
                )
            )
    return rows


def by_account(rows: Iterable[PositionRow]) -> dict[str, list[SnapshotLine]]:
    """The security lines of each account, with the remembered ticker mapping."""
    rows = list(rows)
    mapping = db.source_lines(next(iter({r.source for r in rows}), ""))
    accounts: dict[str, list[SnapshotLine]] = {}
    for row in rows:
        lines = accounts.setdefault(row.account, [])
        if row.support_type == "cash" or not row.quantity:
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
                by_amount=True,
            )
        )
    return accounts


def pending(source: str, rows: Iterable[PositionRow]) -> PendingChoices:
    """What still needs a choice before the sync can run."""
    rows = list(rows)
    placed = db.source_accounts(source)
    lines_map = db.source_lines(source)
    envelopes = {e["name"].upper(): e["name"] for e in db.all_envelopes()}
    assets = db.all_assets()
    accounts: list[PendingAccount] = []
    lines: dict[str, PendingLine] = {}
    for account, snapshot_lines in by_account(rows).items():
        if account not in placed:
            accounts.append(
                PendingAccount(
                    account=account,
                    lines=len(snapshot_lines),
                    envelope=envelopes.get(account.upper()),
                )
            )
        for line in snapshot_lines:
            if line.name in lines_map or line.name in lines:
                continue
            # Suggestion only: the words of the label, matched against assets.
            lines[line.name] = PendingLine(
                label=line.name, symbol=_suggest_asset(line.name, assets)
            )
    return PendingChoices(accounts=accounts, lines=list(lines.values()))


def _suggest_asset(label: str, assets: list[dict]) -> str | None:
    words = {w for w in _words(label)}
    best = None
    best_score = 0
    for asset in assets:
        score = len(words & _words(asset["label"]))
        if score > best_score:
            best_score = score
            best = asset["symbol"]
    return best if best_score > 0 else None


def _words(value: str) -> set[str]:
    import re
    import unicodedata

    normalised = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    return {w for w in re.split(r"[^a-z0-9]+", normalised.lower()) if w and len(w) > 2}


def place(
    source: str,
    placements: list[AccountPlacement],
    mappings: list[LineMapping],
    rows: Iterable[PositionRow],
) -> None:
    """Remember the user's choices. Refuses, writing nothing, if an account is left."""
    envelopes = {p.account: _blank_to_none(p.envelope) for p in placements}
    symbols = {m.label: _blank_to_none(m.symbol) for m in mappings}
    missing = [
        a.account for a in pending(source, rows).accounts if a.account not in envelopes
    ]
    if missing:
        raise ValueError("No envelope chosen for " + ", ".join(missing))
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
    placed = db.source_accounts(source)
    by_envelope: dict[str, list[SnapshotLine]] = {}
    for account, lines in by_account(rows).items():
        envelope = placed.get(account)
        if envelope is None:
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
