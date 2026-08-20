"""Pydantic models for the HTTP surface."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class Position(BaseModel):
    symbol: str
    label: str
    envelope: str
    currency: str
    price_source: str
    quantity: float | None
    prum: float | None
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


class ManualValue(BaseModel):
    value: float = Field(ge=0)

