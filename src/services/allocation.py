"""Monthly split of each envelope across its assets.

Every envelope carries its own amount: there is no global savings figure, and
an envelope never draws from another one. Multipliers only shift money between
assets of the same envelope, so the envelope total is invariant.

An envelope that declares where its strategy starts (see cash.py) spends its
cash instead of its monthly amount, buys whole units by the share, and carries
what it cannot spend to the next month - which is what makes a 600 EUR share
reachable from an envelope funded with 100 EUR a month. Without a start, the
monthly amount is split in euros, the way it always was.
"""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel

from src import calc
from src.databases import sqlite as db
from src.models.schema import (
    EnvelopeAsset,
    PlanAsset,
    PlanEntry,
    ProjectionEntry,
    ProjectionStep,
    WaitingAsset,
)
from src.services import cash, portfolio, prices


class _Spent(BaseModel):
    """The outcome of putting one budget to work."""

    lines: list[PlanAsset]
    waiting: list[EnvelopeAsset]
    carry: float


class _Running(BaseModel):
    """One envelope as the projection walks it forward, month after month."""

    envelope: str
    monthly: float
    tracked: bool
    assets: list[EnvelopeAsset]
    held: dict[str, float]
    carry: float


def _assets_of(
    envelope: str,
    assets: list[dict],
    positions: dict,
    rate: float | None,
    fractional: set[str],
) -> list[EnvelopeAsset]:
    """Everything the split needs about one envelope's assets, in EUR."""
    members = []
    for asset in assets:
        if asset["envelope"] != envelope:
            continue
        position = positions.get(asset["symbol"], {})
        price = position.get("price")
        prum = position.get("prum")
        members.append(
            EnvelopeAsset(
                symbol=asset["symbol"],
                weight=asset["weight"],
                fractional=calc.is_fractional(
                    asset["symbol"], asset["symbol"] in fractional
                ),
                currency=asset["currency"],
                price=price,
                price_eur=portfolio.to_eur(price, asset["currency"], rate),
                prum=prum,
                multiplier=calc.multiplier(price, prum)
                if price and prum
                else calc.MULTIPLIER_NEUTRAL,
                held_eur=portfolio.to_eur(
                    position.get("market_value"), asset["currency"], rate
                ),
            )
        )
    return members


def _split(members: list[EnvelopeAsset], budget: float) -> list[float]:
    """The euro share of `budget` each asset is owed, before any rounding."""
    return calc.renormalize(budget, [(m.weight, m.multiplier) for m in members])


def _line(member: EnvelopeAsset, amount: float, units: int | None = None) -> PlanAsset:
    return PlanAsset(**member.model_dump(), amount=amount, units=units)


def _spend(
    members: list[EnvelopeAsset], budget: float, held: dict[str, float]
) -> _Spent:
    """Turn a budget into lines to act on, given what is already held.

    Fractional assets keep a euro amount; the others pool their shares and are
    bought whole, so a budget too small for any share buys nothing and waits.
    `held` is read and updated, which lets a projection run month after month.
    """
    lines: list[PlanAsset] = []
    pool = 0.0
    by_the_share: list[EnvelopeAsset] = []

    for member, share in zip(members, _split(members, budget)):
        if member.fractional or not member.price_eur:
            lines.append(_line(member, share))
            held[member.symbol] = held.get(member.symbol, 0.0) + share
        else:
            pool += share
            by_the_share.append(member)

    lots, carry = calc.buy_lots(
        pool,
        [
            calc.Candidate(
                symbol=m.symbol,
                price=m.price_eur,
                weight=m.weight * m.multiplier,
                held_value=held.get(m.symbol, m.held_eur),
            )
            for m in by_the_share
        ],
    )
    bought = {lot.symbol: lot for lot in lots}

    waiting = []
    for member in by_the_share:
        lot = bought.get(member.symbol)
        if lot is None:
            # Held but never topped up: not waiting for anything.
            if member.weight:
                waiting.append(member)
            continue
        lines.append(_line(member, lot.amount, lot.units))
        held[member.symbol] = held.get(member.symbol, 0.0) + lot.amount

    return _Spent(lines=lines, waiting=waiting, carry=carry)


def plan(today: date | None = None) -> list[PlanEntry]:
    """One entry per envelope, with what to do with this month's money."""
    today = today or date.today()
    positions = {p["symbol"]: p for p in portfolio.all_positions()}
    assets = db.all_assets()
    rate = prices.eur_usd_rate()
    fractional = db.symbols_traded_in_fractions()

    envelopes = []
    for row in db.all_envelopes():
        monthly = row["monthly_amount"]
        members = _assets_of(row["name"], assets, positions, rate, fractional)
        balance = cash.available(row, today)

        if balance is None:
            budget = monthly
            spent = _Spent(
                lines=[
                    _line(m, amount)
                    for m, amount in zip(members, _split(members, monthly))
                ],
                waiting=[],
                carry=0.0,
            )
        else:
            budget = balance.available
            spent = _spend(members, budget, {})

        envelopes.append(
            PlanEntry(
                envelope=row["name"],
                amount=monthly,
                cash=balance,
                # In EUR, converted asset by asset, like portfolio.summary()
                # does: an envelope holding both EUR and USD lines must not end
                # up as the sum of the two.
                market_value=sum(m.held_eur for m in members),
                assets=spent.lines,
                waiting=[_waiting(m, spent.carry, monthly) for m in spent.waiting],
                budget=budget,
                carry=spent.carry,
            )
        )
    return envelopes


def _waiting(member: EnvelopeAsset, carry: float, monthly: float) -> WaitingAsset:
    """Measured against what was left for shares, not the envelope's whole cash."""
    return WaitingAsset(
        **member.model_dump(),
        missing=max(member.price_eur - carry, 0.0),
        months_left=cash.months_to_afford(member.price_eur, carry, monthly),
    )


def projection(today: date | None = None, months: int = 11) -> list[ProjectionStep]:
    """What the next months look like if nothing changes, month by month.

    At today's prices: the point is to know when the next share becomes
    affordable, not to promise an amount.
    """
    today = today or date.today()
    positions = {p["symbol"]: p for p in portfolio.all_positions()}
    assets = db.all_assets()
    rate = prices.eur_usd_rate()
    fractional = db.symbols_traded_in_fractions()

    states = []
    for row in db.all_envelopes():
        members = _assets_of(row["name"], assets, positions, rate, fractional)
        balance = cash.available(row, today)
        held = {m.symbol: m.held_eur for m in members}
        states.append(
            _Running(
                envelope=row["name"],
                monthly=row["monthly_amount"],
                tracked=balance is not None,
                assets=members,
                held=held,
                # What this month leaves behind, so the first projected month
                # follows on from the note rather than from a clean slate.
                carry=_spend(members, balance.available, held).carry
                if balance
                else 0.0,
            )
        )

    future = []
    for step in range(1, months + 1):
        entries = []
        for state in states:
            if not state.tracked:
                budget = state.monthly
                lines = [
                    _line(m, amount)
                    for m, amount in zip(state.assets, _split(state.assets, budget))
                ]
                carry = 0.0
            else:
                budget = state.carry + state.monthly
                spent = _spend(state.assets, budget, state.held)
                state.carry = carry = spent.carry
                lines = spent.lines
            entries.append(
                ProjectionEntry(
                    envelope=state.envelope,
                    tracked=state.tracked,
                    budget=budget,
                    assets=lines,
                    carry=carry,
                )
            )
        future.append(
            ProjectionStep(
                month=calc.add_months(today.replace(day=1), step), envelopes=entries
            )
        )
    return future
