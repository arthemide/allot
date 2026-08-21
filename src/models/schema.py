"""Pydantic models for the HTTP surface."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


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


class SummaryAsset(BaseModel):
    symbol: str
    label: str
    currency: str
    invested: float
    market_value: float
    gain: float


class SummaryEnvelope(BaseModel):
    envelope: str
    invested: float
    market_value: float
    gain: float
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
