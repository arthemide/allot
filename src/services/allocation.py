"""Monthly split of the savings across envelopes and assets.

The envelope total is invariant: multipliers only shift money between assets of
the same envelope, never across envelopes.
"""

from __future__ import annotations

from src import calc, config
from src.services import portfolio


def plan(settings: config.Config | None = None) -> list[dict]:
    """One entry per envelope, with the amount each of its assets should get."""
    settings = settings or config.load()
    positions = {p["symbol"]: p for p in portfolio.all_positions()}

    envelopes = []
    for name in settings.envelope_shares:
        amount = settings.envelope_amount(name)
        assets = settings.assets_of(name)

        weighted = []
        for asset in assets:
            position = positions.get(asset.ticker, {})
            price = position.get("price")
            prum = position.get("prum")
            multiplier = (
                calc.multiplier(price, prum)
                if asset.price_source != "manual" and price and prum
                else calc.MULTIPLIER_NEUTRAL
            )
            weighted.append((asset, multiplier))

        amounts = calc.renormalize(amount, [(a.weight, m) for a, m in weighted])

        envelopes.append(
            {
                "envelope": name,
                "amount": amount,
                "market_value": sum(
                    positions.get(a.ticker, {}).get("market_value") or 0.0
                    for a in assets
                ),
                "assets": [
                    {
                        "symbol": asset.ticker,
                        "amount": line_amount,
                        "multiplier": multiplier,
                        "currency": asset.currency,
                        "price_source": asset.price_source,
                        "price": positions.get(asset.ticker, {}).get("price"),
                        "prum": positions.get(asset.ticker, {}).get("prum"),
                    }
                    for (asset, multiplier), line_amount in zip(weighted, amounts)
                ],
            }
        )
    return envelopes
