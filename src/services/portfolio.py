"""Turn stored rows into positions, by handing them to calc.py.

Nothing here is stored: every figure is recomputed on each call from the
transactions plus the asset's opening position.
"""

from __future__ import annotations

from datetime import datetime

from src import calc
from src.databases import sqlite as db
from src.services import prices


def _trades(symbol: str) -> list[calc.Trade]:
    return [
        calc.Trade(
            side=row["side"],
            quantity=row["quantity"],
            unit_price=row["unit_price"],
            fees=row["fees"],
        )
        for row in db.transactions_of(symbol)
    ]


def position_of(asset: dict) -> dict:
    """PRUM, quantity, invested, market value and gain for one asset."""
    symbol = asset["symbol"]
    result = calc.position(_trades(symbol), asset["base_quantity"], asset["base_prum"])
    price = prices.current_price(symbol)
    market_value = result.quantity * price if price is not None else None
    gain = market_value - result.invested if market_value is not None else None
    gain_percent = (
        gain / result.invested * 100
        if gain is not None and result.invested
        else None
    )

    return {
        "symbol": symbol,
        "label": asset["label"],
        "envelope": asset["envelope"],
        "currency": asset["currency"],
        "weight": asset["weight"],
        "quantity": result.quantity,
        "prum": result.prum,
        "invested": result.invested,
        "price": price,
        "market_value": market_value,
        "gain": gain,
        "gain_percent": gain_percent,
    }


def all_positions() -> list[dict]:
    return [position_of(asset) for asset in db.all_assets()]


def chart_data(symbol: str) -> dict:
    """Price history, transaction markers and the step PRUM curve.

    The window is pinned to the asset's real transactions: it starts at the
    first one and runs to today. An asset with no transaction falls back to the
    last twelve months.
    """
    asset = db.get_asset(symbol)
    if asset is None:
        return {"symbol": symbol, "prices": [], "transactions": [], "prum": []}

    rows = db.transactions_of(symbol)
    today = datetime.now().date()
    if rows:
        start = datetime.fromisoformat(rows[0]["date"]).date()
    else:
        start = today.replace(year=today.year - 1)

    history = prices.price_history(symbol, start, today)

    # Step PRUM: recompute after each transaction, then hold the value until
    # the next one. Before the first transaction the opening PRUM applies.
    steps = []
    running: list[calc.Trade] = []
    if asset["base_prum"]:
        steps.append({"date": start.isoformat(), "prum": asset["base_prum"]})
    for row in rows:
        running.append(
            calc.Trade(
                side=row["side"],
                quantity=row["quantity"],
                unit_price=row["unit_price"],
                fees=row["fees"],
            )
        )
        current = calc.position(running, asset["base_quantity"], asset["base_prum"])
        steps.append(
            {
                "date": datetime.fromisoformat(row["date"]).date().isoformat(),
                "prum": current.prum,
            }
        )

    return {
        "symbol": symbol,
        "currency": asset["currency"],
        "prices": history,
        "transactions": [
            {
                "id": row["id"],
                "date": datetime.fromisoformat(row["date"]).date().isoformat(),
                "side": row["side"],
                "quantity": row["quantity"],
                "unit_price": row["unit_price"],
                "fees": row["fees"],
            }
            for row in rows
        ],
        "prum": steps,
    }



def _to_eur(value: float | None, currency: str, rate: float | None) -> float:
    """Convert to EUR at the very last moment, for totals only."""
    if not value:
        return 0.0
    if currency == "USD" and rate:
        return value / rate
    return value


def summary() -> dict:
    """Totals across every asset, in EUR, grouped by envelope.

    Native currencies stay untouched everywhere else; conversion happens here
    and nowhere else, because only totals mix currencies.
    """
    rate = prices.eur_usd_rate()
    positions = all_positions()

    envelopes: dict[str, dict] = {}
    for position in positions:
        name = position["envelope"]
        bucket = envelopes.setdefault(
            name, {"envelope": name, "invested": 0.0, "market_value": 0.0, "assets": []}
        )
        currency = position["currency"]
        invested = _to_eur(position["invested"], currency, rate)
        market_value = _to_eur(position["market_value"], currency, rate)
        bucket["invested"] += invested
        bucket["market_value"] += market_value
        bucket["assets"].append(
            {
                "symbol": position["symbol"],
                "label": position["label"],
                "currency": currency,
                "invested": invested,
                "market_value": market_value,
                "gain": market_value - invested,
            }
        )

    for bucket in envelopes.values():
        bucket["gain"] = bucket["market_value"] - bucket["invested"]

    invested = sum(b["invested"] for b in envelopes.values())
    market_value = sum(b["market_value"] for b in envelopes.values())
    return {
        "currency": "EUR",
        "eur_usd_rate": rate,
        "invested": invested,
        "market_value": market_value,
        "gain": market_value - invested,
        "gain_percent": (market_value - invested) / invested * 100 if invested else None,
        "envelopes": sorted(envelopes.values(), key=lambda b: b["envelope"]),
    }
