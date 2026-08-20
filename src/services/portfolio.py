"""Turn stored rows into positions, by handing them to calc.py.

Nothing here is stored: every figure is recomputed on each call from the
transactions plus the asset's opening position.
"""

from __future__ import annotations

from datetime import datetime

from src import calc
from src.databases import sqlite as db
from src.services import prices

MANUAL = "manual"


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
    """PRUM, quantity, invested, market value and gain for one asset.

    A manual asset has no PRUM and no chart: its market value is the number the
    user typed in, and no network call is made for it.
    """
    symbol = asset["symbol"]

    if asset["price_source"] == MANUAL:
        value = asset["manual_value"] or 0.0
        return {
            "symbol": symbol,
            "label": asset["label"],
            "envelope": asset["envelope"],
            "currency": asset["currency"],
            "price_source": MANUAL,
            "quantity": None,
            "prum": None,
            "invested": value,
            "price": None,
            "market_value": value,
            "gain": None,
            "gain_percent": None,
            "actual_quantity": None,
            "quantity_gap": None,
        }

    result = calc.position(_trades(symbol), asset["base_quantity"], asset["base_prum"])
    actual = asset.get("actual_quantity")
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
        "price_source": asset["price_source"],
        "quantity": result.quantity,
        "prum": result.prum,
        "invested": result.invested,
        "price": price,
        "market_value": market_value,
        "gain": gain,
        "gain_percent": gain_percent,
        "actual_quantity": actual,
        "quantity_gap": (actual - result.quantity) if actual is not None else None,
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
    if asset is None or asset["price_source"] == MANUAL:
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


def simulate(
    symbol: str,
    amount: float | None = None,
    fees: float = 0.0,
    target_prum: float | None = None,
) -> dict:
    """What a buy would do to the PRUM, and what reaching a target would cost."""
    asset = db.get_asset(symbol)
    if asset is None or asset["price_source"] == MANUAL:
        raise ValueError("simulation needs a priced asset")

    price = prices.current_price(symbol)
    if price is None:
        raise ValueError("no current price for this asset")

    current = calc.position(_trades(symbol), asset["base_quantity"], asset["base_prum"])
    result = {
        "symbol": symbol,
        "currency": asset["currency"],
        "price": price,
        "quantity": current.quantity,
        "prum": current.prum,
        "buy": None,
        "target": None,
    }

    if amount is not None:
        bought, new_prum = calc.prum_after_buy(
            current.quantity, current.prum, price, amount, fees
        )
        result["buy"] = {
            "amount": amount,
            "fees": fees,
            "quantity": bought,
            "new_prum": new_prum,
        }

    if target_prum is not None:
        needed = calc.quantity_for_target_prum(
            current.quantity, current.prum, price, target_prum
        )
        if needed is None:
            reason = (
                "the price is at or above the target: buying can only raise the PRUM"
                if price >= target_prum
                else "the target is above the current PRUM"
            )
            result["target"] = {
                "target_prum": target_prum,
                "reachable": False,
                "reason": reason,
            }
        else:
            quantity, cost = needed
            result["target"] = {
                "target_prum": target_prum,
                "reachable": True,
                "quantity": quantity,
                "amount": cost,
            }

    return result
