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


def _unreadable(row: PositionRow, mapping: dict[str, str | None]) -> bool:
    """A fund already mapped to a ticker, read this time without its units.

    The site changed, or the reading failed on that line: taking it for an
    amount would report the fund sold. It is held back as unresolved instead.
    """
    return _is_amount(row) and mapping.get(row.label) is not None


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
    # A guess never points at a ticker another line of the source already has.
    taken = {symbol for symbol in mapped.values() if symbol}
    assets = [a for a in db.all_assets() if a["symbol"] not in taken]
    common = _common_words(source, rows)
    accounts: list[AccountChoice] = []
    lines: dict[str, PendingLine] = {}
    for account, snapshot_lines in by_account(source, rows).items():
        if account not in placed:
            accounts.append(
                AccountChoice(
                    account=account,
                    lines=len(snapshot_lines),
                    envelope=_offer(envelopes.get(account.upper()), source),
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
                symbol=_suggest_asset(line.name, assets, common),
            )
    return PendingChoices(accounts=accounts, lines=list(lines.values()))


def _offer(envelope: str | None, source: str) -> str | None:
    """An envelope of the account's name, unless another source syncs into it."""
    return None if _taken_by(envelope, source) else envelope


def _common_words(source: str, rows: list[PositionRow]) -> set[str]:
    """Words that tell no fund apart: the source's name, and any word most
    of the reading's labels share ("afer" in every Afer fund)."""
    labels = [_words(row.label) for row in rows if not _is_amount(row)]
    counts: dict[str, int] = {}
    for words in labels:
        for word in words:
            counts[word] = counts.get(word, 0) + 1
    shared = {w for w, n in counts.items() if len(labels) > 1 and n * 2 > len(labels)}
    return shared | _words(source) | _words(registry.get(source).name)


def _suggest_asset(label: str, assets: list[dict], common: set[str]) -> str | None:
    """The asset whose label shares the most telling words with the line's.

    A guess the user confirms, never an answer: the front shows it as a hint.
    """
    words = _words(label) - common
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
    """Remember the user's choices. Refuses, writing nothing, if one is wrong.

    Every new account needs an answer; an empty one leaves the account out. A
    line is answered with a ticker, or with None to leave it out; a line not
    answered is asked again next time. An envelope that does not exist yet is
    created, as adding an asset would.

    Refused: an envelope another source already syncs into, since each source
    would take the other's assets for sold; a ticker another line of the
    source already has, or that lives in another envelope; a fund held by
    accounts placed in different envelopes, since an asset sits in one.
    """
    rows = list(rows)
    envelopes = {p.account: _blank_to_none(p.envelope) for p in placements}
    symbols = {m.label: _ticker(m.symbol) for m in mappings}
    missing = [
        a.account for a in pending(source, rows).accounts if a.account not in envelopes
    ]
    if missing:
        raise ValueError(f"No envelope chosen for {', '.join(missing)}.")
    for account, envelope in envelopes.items():
        taken = _taken_by(envelope, source)
        if taken:
            raise ValueError(
                f"{envelope} already syncs {taken}. Pick another envelope for "
                f"{account}: two sources in one envelope would each zero the "
                "other's assets."
            )
    _check_tickers(source, symbols, {**db.source_accounts(source), **envelopes}, rows)

    for account, envelope in envelopes.items():
        if envelope is not None and db.get_envelope(envelope) is None:
            db.upsert_envelope(envelope, 0.0)
        db.set_source_account(source, account, envelope)
    for label, symbol in symbols.items():
        db.set_source_line(source, label, symbol)


def _check_tickers(
    source: str,
    symbols: dict[str, str | None],
    placed: dict[str, str | None],
    rows: list[PositionRow],
) -> None:
    """Refuse a ticker choice that would make two lines, or two envelopes, fight
    over one asset."""
    # Every ticker already claimed, but by the lines being answered again.
    owners = {
        symbol: label
        for label, symbol in db.source_lines(source).items()
        if symbol and label not in symbols
    }
    envelopes_of: dict[str, set[str]] = {}
    for row in rows:
        envelope = placed.get(row.account)
        if envelope is not None and not _is_amount(row):
            envelopes_of.setdefault(row.label, set()).add(envelope)
    for label, symbol in symbols.items():
        if symbol is None:
            continue
        if owners.setdefault(symbol, label) != label:
            raise ValueError(
                f"{symbol} is already the ticker of {owners[symbol]}. Two funds "
                "cannot share one asset."
            )
        held_in = envelopes_of.get(label, set())
        if len(held_in) > 1:
            raise ValueError(
                f"{label} is held in {', '.join(sorted(held_in))}, but an asset "
                "sits in one envelope. Place its accounts in one envelope, or "
                "leave the fund out."
            )
        asset = db.get_asset(symbol)
        if asset is not None and held_in and asset["envelope"] not in held_in:
            raise ValueError(
                f"{symbol} is tracked in {asset['envelope']}, not in "
                f"{next(iter(held_in))}. Pick another ticker for {label}, or move "
                "the asset first."
            )


def _taken_by(envelope: str | None, source: str) -> str | None:
    """The other source and account already syncing into `envelope`, if any."""
    if envelope is None:
        return None
    for owner in db.envelope_sources(envelope):
        if owner["source"] != source:
            name = registry.get(owner["source"]).name
            return f"{name}'s account {owner['account']}"
    return None


def _blank_to_none(value: str | None) -> str | None:
    """A choice typed as spaces is no choice: the account is left out."""
    return (value or "").strip() or None


def _ticker(value: str | None) -> str | None:
    """A ticker as Yahoo spells it; None leaves the line out."""
    name = _blank_to_none(value)
    return name.upper() if name else None


def apply(source: str, rows: Iterable[PositionRow]) -> dict:
    """Sync every placed account into its envelope; return one ImportReport dict.

    A source that owns its envelopes zeroes whatever of the envelope it no
    longer reports, and moves into it an asset filed elsewhere. One that does
    not only zeroes the assets its lines map to, and never moves an asset:
    another asset of the envelope, tracked by hand, is left alone. Another
    source never shares the envelope (`place` refuses it).

    Lines of the same asset are added up first: the same fund held by two
    accounts of one envelope is one position. Held in two envelopes, or read
    without its units, it is held back unresolved, which zeroes nothing.
    """
    rows = list(rows)
    owns = registry.get(source).owns_envelope
    placed = db.source_accounts(source)
    mapping = db.source_lines(source)
    scope = None if owns else {symbol for symbol in mapping.values() if symbol}

    by_envelope: dict[str, list[SnapshotLine]] = {}
    held_back: dict[str, list[dict]] = {}
    for account, lines in by_account(source, rows).items():
        envelope = placed.get(account)
        if envelope is None:
            # Left out by the user, or not placed yet (pending says so).
            continue
        by_envelope.setdefault(envelope, []).extend(lines)
    for row in rows:
        envelope = placed.get(row.account)
        if envelope is not None and _unreadable(row, mapping):
            held_back.setdefault(envelope, []).append(
                {"isin": row.isin, "name": f"{row.label} (no units read)"}
            )

    envelopes_of: dict[str, set[str]] = {}
    for envelope, lines in by_envelope.items():
        for line in lines:
            if line.symbol:
                envelopes_of.setdefault(line.symbol, set()).add(envelope)
    for envelope, lines in by_envelope.items():
        kept = []
        for line in lines:
            if line.symbol and len(envelopes_of[line.symbol]) > 1:
                where = ", ".join(sorted(envelopes_of[line.symbol]))
                held_back.setdefault(envelope, []).append(
                    {"isin": line.isin, "name": f"{line.name} (held in {where})"}
                )
            else:
                kept.append(line)
        by_envelope[envelope] = _add_up(kept)

    merged = {
        "imported": [],
        "unresolved": [],
        "elsewhere": [],
        "conflicts": [],
        "available": _available(rows, placed, mapping),
        "total": 0,
    }
    for envelope in sorted(by_envelope.keys() | held_back.keys()):
        report = portfolio_import.apply_snapshot(
            envelope,
            by_envelope.get(envelope, []),
            authoritative=True,
            scope=scope,
            relocate=owns,
            held_back=held_back.get(envelope, []),
        )
        for key in ("imported", "unresolved", "elsewhere", "conflicts"):
            merged[key].extend(report[key])
        merged["total"] += report["total"]
    return merged


def _add_up(lines: list[SnapshotLine]) -> list[SnapshotLine]:
    """One line per asset: quantities added, PRUM weighted by quantity."""
    groups: dict[str, list[SnapshotLine]] = {}
    out: list[SnapshotLine] = []
    for line in lines:
        key = line.symbol or line.isin
        if key is None:
            out.append(line)  # Unresolved anyway: nothing to add it to.
        else:
            groups.setdefault(key, []).append(line)
    for group in groups.values():
        if len(group) == 1:
            out.append(group[0])
            continue
        quantity = sum(line.quantity for line in group)
        priced = all(line.prum is not None for line in group)
        prum = (
            sum(line.quantity * line.prum for line in group) / quantity
            if priced and quantity
            else None
        )
        out.append(group[0].model_copy(update={"quantity": quantity, "prum": prum}))
    return out


def _available(
    rows: list[PositionRow],
    placed: dict[str, str | None],
    mapping: dict[str, str | None],
) -> list[dict]:
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
        if _is_amount(row)
        and not _unreadable(row, mapping)
        and row.value
        and placed.get(row.account) is not None
    ]
