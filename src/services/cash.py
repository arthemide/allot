"""What is sitting in cash in an envelope, derived rather than stored.

    available = opening_cash
              + monthly_amount * months since the start (current month included)
              - buys since that date
              + sells since that date

The figure is a plan being followed, not a bank balance: dividends, custody
fees and skipped months are not modelled. When it stops matching the
statement, a new start is recorded and the derivation restarts from there, so
an error never survives past the last recalibration.

An envelope without a start row tracks no cash, and everything here returns
None for it.
"""

from __future__ import annotations

import math
from datetime import date, datetime

from src import calc
from src.databases import sqlite as db
from src.models.schema import CashBalance
from src.services import portfolio, prices


def available(envelope: dict, today: date | None = None) -> CashBalance | None:
    """The envelope's cash, with the terms it is made of.

    The terms come back with it so the figure can be argued with against a
    statement.
    """
    start = db.get_envelope_start(envelope["name"])
    if start is None:
        return None

    today = today or date.today()
    started_on = datetime.fromisoformat(start["started_on"]).date()
    months = calc.months_elapsed(started_on, today)
    paid_in = envelope["monthly_amount"] * months

    rate = prices.eur_usd_rate()
    spent = 0.0
    returned = 0.0
    for row in db.envelope_transactions(envelope["name"], start["started_on"]):
        gross = row["quantity"] * row["unit_price"]
        if row["side"] == "buy":
            spent += portfolio.to_eur(gross + row["fees"], row["currency"], rate)
        else:
            returned += portfolio.to_eur(gross - row["fees"], row["currency"], rate)

    amount = start["opening_cash"] + paid_in - spent + returned
    return CashBalance(
        started_on=start["started_on"],
        opening_cash=start["opening_cash"],
        months=months,
        paid_in=paid_in,
        spent=spent,
        returned=returned,
        # More spent than paid in means the strategy was not followed; a debt
        # here would only propagate the error.
        available=max(amount, 0.0),
    )


def months_to_afford(price: float, current: float, monthly_amount: float) -> int | None:
    """How many more months before the envelope can pay `price`, None if never."""
    missing = price - current
    if missing <= 0:
        return 0
    if monthly_amount <= 0:
        return None
    return math.ceil(missing / monthly_amount)
