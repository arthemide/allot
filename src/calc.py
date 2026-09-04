"""Pure calculation helpers.

No database access, no network, no I/O. Everything here takes plain numbers or
plain pydantic models and returns plain numbers. This is the only module worth
unit-testing.

All amounts and prices are expressed in the asset's native currency.
"""

from __future__ import annotations

from datetime import date

from src.models.schema import Candidate, Lot, PositionResult, Trade

# Relative gap to the PRUM beyond which the monthly amount is modulated.
MODULATION_BAND = 0.10
MULTIPLIER_BELOW = 1.5
MULTIPLIER_ABOVE = 0.5
MULTIPLIER_NEUTRAL = 1.0


def position(
    trades: list[Trade],
    base_quantity: float = 0.0,
    base_prum: float | None = None,
) -> PositionResult:
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
        return PositionResult(quantity=0.0, prum=0.0, invested=0.0)

    prum = bought_cost / bought_quantity
    quantity = bought_quantity - sold_quantity
    return PositionResult(quantity=quantity, prum=prum, invested=quantity * prum)


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


# How Yahoo names crypto pairs: BTC-EUR, ETH-USD.
FRACTIONAL_SUFFIXES = ("-USD", "-EUR", "-GBP")


def is_fractional(symbol: str, traded_in_fractions: bool = False) -> bool:
    """Whether the asset can be bought by the amount rather than by the share.

    Nothing to configure: a fractional quantity already recorded settles it,
    the ticker is the clue until then. Whole shares is the careful default -
    it makes an envelope save up rather than produce an order a broker would
    refuse.
    """
    return traded_in_fractions or symbol.upper().endswith(FRACTIONAL_SUFFIXES)


def months_elapsed(start: date, today: date) -> int:
    """How many monthly contributions have landed between the two dates.

    The current month counts: a strategy started on 1 September has paid in
    once by 15 September. A start in the future counts for nothing.
    """
    months = (today.year - start.year) * 12 + (today.month - start.month) + 1
    return max(months, 0)


def add_months(first_of_month: date, count: int) -> date:
    """The 1st of the month `count` months after the one given."""
    month = first_of_month.month - 1 + count
    return date(first_of_month.year + month // 12, month % 12 + 1, 1)


# One share per pass: a 10 000 EUR budget against a 1 EUR share would
# otherwise loop ten thousand times.
MAX_LOTS = 500


def buy_lots(budget: float, candidates: list[Candidate]) -> tuple[list[Lot], float]:
    """Spend `budget` on whole units, most under-weighted asset first.

    One unit per pass, recomputing the shares each time, so the order corrects
    itself as the money is spent. A budget too small for anything buys nothing
    at all - which is the point, a third of a share cannot be ordered.

    Returns the lots and what is left to carry to the next month.
    """
    usable = [c for c in candidates if c.price > 0 and c.weight > 0]
    if not usable:
        return [], budget

    values = {c.symbol: c.held_value for c in usable}
    units: dict[str, int] = {}
    total_weight = sum(c.weight for c in usable)

    for _ in range(MAX_LOTS):
        affordable = [c for c in usable if c.price <= budget]
        if not affordable:
            break

        total_value = sum(values.values())

        def drift(candidate: Candidate) -> float:
            target = candidate.weight / total_weight
            actual = values[candidate.symbol] / total_value if total_value else 0.0
            return target - actual

        # Ties settle on the dearer share: the cheap one can still be bought
        # with what is left, the reverse starves it for another month.
        pick = max(affordable, key=lambda c: (drift(c), c.price, c.symbol))
        budget -= pick.price
        values[pick.symbol] += pick.price
        units[pick.symbol] = units.get(pick.symbol, 0) + 1

    lots = [
        Lot(symbol=c.symbol, units=units[c.symbol], amount=units[c.symbol] * c.price)
        for c in usable
        if c.symbol in units
    ]
    return lots, budget
