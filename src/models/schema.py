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
    actual_quantity: float | None = None
    quantity_gap: float | None = None


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


class SimulationRequest(BaseModel):
    """Either an amount to invest, a target PRUM, or both."""

    amount: float | None = Field(default=None, gt=0)
    fees: float = Field(default=0.0, ge=0)
    target_prum: float | None = Field(default=None, gt=0)


class BuySimulation(BaseModel):
    amount: float
    fees: float
    quantity: float
    new_prum: float


class TargetSimulation(BaseModel):
    target_prum: float
    reachable: bool
    reason: str | None = None
    quantity: float | None = None
    amount: float | None = None


class Simulation(BaseModel):
    symbol: str
    currency: str
    price: float
    quantity: float
    prum: float
    buy: BuySimulation | None = None
    target: TargetSimulation | None = None


class ActualQuantity(BaseModel):
    quantity: float | None = Field(default=None, ge=0)
