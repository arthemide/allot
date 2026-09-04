"""The models the app passes around.

Everything above `Trade` is the HTTP surface; everything below it is internal
and never leaves the process.
"""

from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class Position(BaseModel):
    symbol: str
    label: str
    envelope: str
    currency: str
    weight: float
    base_quantity: float
    base_prum: float | None
    quantity: float
    prum: float
    invested: float
    price: float | None
    market_value: float | None
    gain: float | None
    gain_percent: float | None


class PricePoint(BaseModel):
    date: str
    price: float


class PrumPoint(BaseModel):
    date: str
    prum: float


class Transaction(BaseModel):
    id: int
    date: str
    side: Literal["buy", "sell"]
    quantity: float
    unit_price: float
    fees: float


class Chart(BaseModel):
    symbol: str
    currency: str = "EUR"
    prices: list[PricePoint] = []
    transactions: list[Transaction] = []
    prum: list[PrumPoint] = []


class TransactionCreate(BaseModel):
    symbol: str
    date: str
    side: Literal["buy", "sell"]
    quantity: float = Field(gt=0)
    unit_price: float = Field(gt=0)
    fees: float = Field(default=0.0, ge=0)


class SearchHit(BaseModel):
    """One ticker search result, price included so a dead symbol is visible."""

    symbol: str
    label: str
    exchange: str
    type: str
    currency: str | None
    price: float | None


class AssetCreate(BaseModel):
    symbol: str
    label: str
    envelope: str
    currency: str
    weight: float = Field(default=1.0, ge=0)


class AssetUpdate(BaseModel):
    label: str
    envelope: str
    weight: float = Field(ge=0)


class OpeningPosition(BaseModel):
    """A holding that predates tracking, as it reads on a statement."""

    quantity: float = Field(ge=0)
    invested: float | None = Field(default=None, ge=0)


class Envelope(BaseModel):
    name: str
    monthly_amount: float = Field(ge=0)
    # Only set when the envelope tracks its cash; see EnvelopeStart.
    started_on: str | None = None
    opening_cash: float | None = None
    available: float | None = None


class EnvelopeStart(BaseModel):
    """Where a strategy starts, or where it is recalibrated.

    `opening_cash` is what is actually sitting in the envelope on that date -
    0 for a strategy that starts from nothing.
    """

    started_on: str
    opening_cash: float = Field(default=0.0, ge=0)


class SummaryAsset(BaseModel):
    symbol: str
    label: str
    currency: str
    invested: float
    market_value: float
    gain: float
    gain_percent: float | None


class SummaryEnvelope(BaseModel):
    envelope: str
    invested: float
    market_value: float
    gain: float
    gain_percent: float | None
    assets: list[SummaryAsset]


class Summary(BaseModel):
    """Everything totalled in EUR; the only place currencies are mixed."""

    currency: str
    eur_usd_rate: float | None
    invested: float
    market_value: float
    gain: float
    gain_percent: float | None
    envelopes: list[SummaryEnvelope]


class FeedUrl(BaseModel):
    """Where a calendar subscribes, and whether that address carries a token."""

    url: str
    token: bool


class Login(BaseModel):
    """The one credential this app knows about."""

    password: str


class Session(BaseModel):
    """What the front needs at boot to decide between login screen and app."""

    required: bool
    authenticated: bool


class Trade(BaseModel):
    """A single buy or sell."""

    model_config = ConfigDict(frozen=True)

    side: str  # "buy" or "sell"
    quantity: float
    unit_price: float
    fees: float = 0.0


class PositionResult(BaseModel):
    """A holding, recomputed from trades. Never stored."""

    model_config = ConfigDict(frozen=True)

    quantity: float
    prum: float
    invested: float


class Candidate(BaseModel):
    """One asset competing for the envelope's cash, everything in EUR."""

    model_config = ConfigDict(frozen=True)

    symbol: str
    price: float
    # Weight times the PRUM multiplier: the share this asset should hold.
    weight: float
    # What is already held, so the split follows the drift.
    held_value: float = 0.0


class Lot(BaseModel):
    """Whole units to buy of one asset."""

    model_config = ConfigDict(frozen=True)

    symbol: str
    units: int
    amount: float


class CashBalance(BaseModel):
    """What is sitting in cash in an envelope, derived rather than stored.

    The terms travel with the figure so it can be argued with against a
    statement.
    """

    model_config = ConfigDict(frozen=True)

    started_on: str
    opening_cash: float
    months: int
    paid_in: float
    spent: float
    returned: float
    available: float


class EnvelopeAsset(BaseModel):
    """One asset of an envelope, as the split needs it: everything in EUR."""

    model_config = ConfigDict(frozen=True)

    symbol: str
    weight: float
    fractional: bool
    currency: str
    price: float | None
    # 0.0 when the quote is missing, so the arithmetic never guards for None.
    price_eur: float
    prum: float | None
    multiplier: float
    held_eur: float


class PlanAsset(EnvelopeAsset):
    """One asset line in the monthly plan: an amount, or a number of shares."""

    amount: float
    units: int | None = None


class WaitingAsset(EnvelopeAsset):
    """An asset the envelope is saving up for but cannot afford yet."""

    missing: float
    months_left: int | None


class PlanEntry(BaseModel):
    """One envelope's plan for the month."""

    model_config = ConfigDict(frozen=True)

    envelope: str
    amount: float
    cash: CashBalance | None
    market_value: float
    assets: list[PlanAsset]
    waiting: list[WaitingAsset]
    budget: float
    carry: float


class ProjectionEntry(BaseModel):
    """One envelope's projected plan for a future month."""

    model_config = ConfigDict(frozen=True)

    envelope: str
    tracked: bool
    budget: float
    assets: list[PlanAsset]
    carry: float


class ProjectionStep(BaseModel):
    """One month of projection: every envelope's planned state."""

    model_config = ConfigDict(frozen=True)

    month: date
    envelopes: list[ProjectionEntry]
