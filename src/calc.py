"""Pure calculation helpers.

No database access, no network, no I/O. Everything here takes plain numbers or
plain pydantic models and returns plain numbers. This is the only module worth
unit-testing.

All amounts and prices are expressed in the asset's native currency.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

# Relative gap to the PRUM beyond which the monthly amount is modulated.
MODULATION_BAND = 0.10
MULTIPLIER_BELOW = 1.5
MULTIPLIER_ABOVE = 0.5
MULTIPLIER_NEUTRAL = 1.0


class Trade(BaseModel):
    """A single buy or sell."""

    model_config = ConfigDict(frozen=True)

    side: str  # "buy" or "sell"
    quantity: float
    unit_price: float
    fees: float = 0.0


class Position(BaseModel):
    """A holding, recomputed from trades. Never stored."""

    model_config = ConfigDict(frozen=True)

    quantity: float
    prum: float
    invested: float


def position(
    trades: list[Trade],
    base_quantity: float = 0.0,
    base_prum: float | None = None,
) -> Position:
    """Recompute quantity and PRUM from an opening position plus trades.

    PRUM = (sum(buy_quantity * buy_price) + sum(fees)) / sum(buy_quantity)

    A sell reduces the quantity held and leaves the PRUM untouched, which is
    why sells contribute to neither term of the ratio.

    `base_quantity` / `base_prum` carry a holding that predates transaction
    tracking; it behaves exactly like an initial buy.
    """
    bought_quantity = base_quantity
    bought_cost = base_quantity * (base_prum or 0.0)
    sold_quantity = 0.0

    for trade in trades:
        if trade.side == "buy":
            bought_quantity += trade.quantity
            bought_cost += trade.quantity * trade.unit_price + trade.fees
        elif trade.side == "sell":
            sold_quantity += trade.quantity
        else:
            raise ValueError(f"unknown side: {trade.side!r}")

    if bought_quantity == 0:
        return Position(quantity=0.0, prum=0.0, invested=0.0)

    prum = bought_cost / bought_quantity
    quantity = bought_quantity - sold_quantity
    return Position(quantity=quantity, prum=prum, invested=quantity * prum)


def prum_after_buy(
    quantity: float, prum: float, price: float, amount: float, fees: float = 0.0
) -> tuple[float, float]:
    """PRUM after investing `amount` (fees included) at `price`.

    q = (amount - fees) / price
    prum' = (quantity * prum + amount) / (quantity + q)

    Returns (bought_quantity, new_prum).
    """
    if price <= 0:
        raise ValueError("price must be positive")
    bought = (amount - fees) / price
    total = quantity + bought
    if total == 0:
        return 0.0, 0.0
    return bought, (quantity * prum + amount) / total


def quantity_for_target_prum(
    quantity: float, prum: float, price: float, target: float
) -> tuple[float, float] | None:
    """Quantity and amount needed to bring the PRUM down to `target`.

    q = quantity * (prum - target) / (target - price)

    Only defined for price < target < prum. Returns None when the target
    cannot be reached by buying, so callers can say so explicitly instead of
    showing a negative number.
    """
    if not (price < target < prum):
        return None
    needed = quantity * (prum - target) / (target - price)
    return needed, needed * price


def multiplier(price: float, prum: float) -> float:
    """Monthly amount multiplier, from the relative gap to the PRUM.

    gap < -10%  -> 1.5   (cheaper than our average, buy more)
    gap > +10%  -> 0.5   (dearer than our average, buy less)
    otherwise   -> 1
    """
    if prum <= 0:
        return MULTIPLIER_NEUTRAL
    gap = (price - prum) / prum
    if gap < -MODULATION_BAND:
        return MULTIPLIER_BELOW
    if gap > MODULATION_BAND:
        return MULTIPLIER_ABOVE
    return MULTIPLIER_NEUTRAL


def renormalize(
    envelope_amount: float, weighted: list[tuple[float, float]]
) -> list[float]:
    """Split an envelope across its assets, applying the multipliers.

    amount_i = envelope_amount * (weight_i * mult_i) / sum(weight_j * mult_j)

    The envelope total is invariant: an envelope never draws from another one.
    On a single-asset envelope the multiplier therefore has no effect, which is
    intended.
    """
    products = [weight * mult for weight, mult in weighted]
    total = sum(products)
    if total == 0:
        return [0.0] * len(products)
    return [envelope_amount * p / total for p in products]
