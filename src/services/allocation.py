"""Monthly split of each envelope across its assets.

Every envelope carries its own amount: there is no global savings figure, and
an envelope never draws from another one. Multipliers only shift money between
assets of the same envelope, so the envelope total is invariant.
"""

from __future__ import annotations

from src import calc
from src.databases import sqlite as db
from src.services import portfolio


def plan() -> list[dict]:
    """One entry per envelope, with the amount each of its assets should get."""
    positions = {p["symbol"]: p for p in portfolio.all_positions()}
    assets = db.all_assets()

    envelopes = []
    for envelope in db.all_envelopes():
        name = envelope["name"]
        amount = envelope["monthly_amount"]
        members = [a for a in assets if a["envelope"] == name]

        weighted = []
        for asset in members:
            position = positions.get(asset["symbol"], {})
            price = position.get("price")
            prum = position.get("prum")
            multiplier = (
                calc.multiplier(price, prum)
                if price and prum
                else calc.MULTIPLIER_NEUTRAL
            )
            weighted.append((asset, multiplier))

        amounts = calc.renormalize(
            amount, [(a["weight"], m) for a, m in weighted]
        )

        envelopes.append(
            {
                "envelope": name,
                "amount": amount,
                "market_value": sum(
                    positions.get(a["symbol"], {}).get("market_value") or 0.0
                    for a in members
                ),
                "assets": [
                    {
                        "symbol": asset["symbol"],
                        "amount": line_amount,
                        "multiplier": multiplier,
                        "currency": asset["currency"],
                        "price": positions.get(asset["symbol"], {}).get("price"),
                        "prum": positions.get(asset["symbol"], {}).get("prum"),
                    }
                    for (asset, multiplier), line_amount in zip(weighted, amounts)
                ],
            }
        )
    return envelopes
