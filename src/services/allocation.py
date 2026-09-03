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

from src import calc
from src.databases import sqlite as db
from src.models.schema import (
    PlanAsset,
    PlanEntry,
    ProjectionEntry,
    ProjectionStep,
    WaitingAsset,
)
from src.services import cash, portfolio, prices


def _members(
    envelope: str,
    assets: list[dict],
    positions: dict,
    rate: float | None,
    fractional: set[str],
):
    """Everything the split needs about one envelope's assets, in EUR."""
    members = []
    for asset in assets:
        if asset["envelope"] != envelope:
            continue
        position = positions.get(asset["symbol"], {})
        price = position.get("price")
        prum = position.get("prum")
        multiplier = (
            calc.multiplier(price, prum) if price and prum else calc.MULTIPLIER_NEUTRAL
        )
        members.append(
            {
                "symbol": asset["symbol"],
                "weight": asset["weight"],
                "fractional": calc.is_fractional(
                    asset["symbol"], asset["symbol"] in fractional
                ),
                "currency": asset["currency"],
                "price": price,
                "price_eur": portfolio.to_eur(price, asset["currency"], rate),
                "prum": prum,
                "multiplier": multiplier,
                "held_eur": portfolio.to_eur(
                    position.get("market_value"), asset["currency"], rate
                ),
            }
        )
    return members


def _split(members: list[dict], budget: float) -> list[float]:
    """The euro share of `budget` each asset is owed, before any rounding."""
    return calc.renormalize(budget, [(m["weight"], m["multiplier"]) for m in members])


def _spend(members: list[dict], budget: float, held: dict[str, float]) -> dict:
    """Turn a budget into lines to act on, given what is already held.

    Fractional assets keep a euro amount; the others pool their shares and are
    bought whole, so a budget too small for any share buys nothing and waits.
    `held` is read and updated, which lets a projection run month after month.
    """
    shares = _split(members, budget)
    lines: list[dict] = []
    pool = 0.0
    lots_wanted = []

    for member, share in zip(members, shares):
        if member["fractional"] or not member["price_eur"]:
            lines.append({**member, "amount": share, "units": None})
            held[member["symbol"]] = held.get(member["symbol"], 0.0) + share
        else:
            pool += share
            lots_wanted.append(member)

    lots, carry = calc.buy_lots(
        pool,
        [
            calc.Candidate(
                symbol=m["symbol"],
                price=m["price_eur"],
                weight=m["weight"] * m["multiplier"],
                held_value=held.get(m["symbol"], m["held_eur"]),
            )
            for m in lots_wanted
        ],
    )
    bought = {lot.symbol: lot for lot in lots}

    waiting = []
    for member in lots_wanted:
        lot = bought.get(member["symbol"])
        if lot is None:
            if member["weight"]:
                waiting.append(member)
            continue
        lines.append({**member, "amount": lot.amount, "units": lot.units})
        held[member["symbol"]] = held.get(member["symbol"], 0.0) + lot.amount

    return {"lines": lines, "waiting": waiting, "carry": carry}


def plan(today: date | None = None) -> list[PlanEntry]:
    """One entry per envelope, with what to do with this month's money."""
    today = today or date.today()
    positions = {p["symbol"]: p for p in portfolio.all_positions()}
    assets = db.all_assets()
    rate = prices.eur_usd_rate()
    fractional = db.symbols_traded_in_fractions()

    envelopes = []
    for envelope in db.all_envelopes():
        name = envelope["name"]
        monthly = envelope["monthly_amount"]
        members = _members(name, assets, positions, rate, fractional)
        balance = cash.available(envelope, today)

        if balance is None:
            shares = _split(members, monthly)
            entry = {
                "budget": monthly,
                "lines": [
                    {**m, "amount": amount, "units": None}
                    for m, amount in zip(members, shares)
                ],
                "waiting": [],
                "carry": 0.0,
            }
        else:
            entry = _spend(members, balance.available, {})
            entry["budget"] = balance.available

        # Measured against what was left for whole shares, not against the
        # envelope's whole cash: the fractional lines took their part already.
        for member in entry["waiting"]:
            member["missing"] = max(member["price_eur"] - entry["carry"], 0.0)
            member["months_left"] = cash.months_to_afford(
                member["price_eur"], entry["carry"], monthly
            )

        envelopes.append(
            PlanEntry(
                envelope=name,
                amount=monthly,
                cash=balance,
                # In EUR, converted asset by asset, like portfolio.summary()
                # does: an envelope holding both EUR and USD lines must not end
                # up as the sum of the two.
                market_value=sum(m["held_eur"] for m in members),
                assets=[PlanAsset(**a) for a in entry["lines"]],
                waiting=[WaitingAsset(**w) for w in entry["waiting"]],
                budget=entry["budget"],
                carry=entry["carry"],
            )
        )
    return envelopes


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
    for envelope in db.all_envelopes():
        members = _members(envelope["name"], assets, positions, rate, fractional)
        balance = cash.available(envelope, today)
        held = {m["symbol"]: m["held_eur"] for m in members}
        state = {
            "envelope": envelope["name"],
            "monthly": envelope["monthly_amount"],
            "members": members,
            "held": held,
            "tracked": balance is not None,
            # What this month leaves behind, so the first projected month
            # follows on from the note rather than from a clean slate.
            "carry": _spend(members, balance.available, held)["carry"]
            if balance
            else 0.0,
        }
        states.append(state)

    future = []
    for step in range(1, months + 1):
        month = calc.add_months(today.replace(day=1), step)
        entries = []
        for state in states:
            if not state["tracked"]:
                budget = state["monthly"]
                shares = _split(state["members"], budget)
                lines = [
                    {**m, "amount": amount, "units": None}
                    for m, amount in zip(state["members"], shares)
                ]
                carry = 0.0
            else:
                budget = state["carry"] + state["monthly"]
                spent = _spend(state["members"], budget, state["held"])
                state["carry"] = carry = spent["carry"]
                lines = spent["lines"]
            entries.append(
                ProjectionEntry(
                    envelope=state["envelope"],
                    tracked=state["tracked"],
                    budget=budget,
                    assets=[PlanAsset(**a) for a in lines],
                    carry=carry,
                )
            )
        future.append(ProjectionStep(month=month, envelopes=entries))
    return future
