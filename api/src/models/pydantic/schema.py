from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class StockSchema(BaseModel):
    id: Optional[str] = None
    symbol: str
    shares_number: int
    cost: Optional[float] = None
    today_price: Optional[float] = None
    prum: float
    market_value: Optional[float] = None
    gain_loss: Optional[float] = None
    gain_loss_percentage: Optional[float] = None
    current_repartition: float
    target_repartition: float
    arbitration_threshold: float
    threshold_to_alert: float


class FundSchema(BaseModel):
    id: Optional[str] = None
    fund_name: str
    stocks: list[StockSchema]
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    total_cost: Optional[float] = None
    total_market_value: Optional[float] = None
    total_gain_loss: Optional[float] = None
    average_gain_loss_percentage: Optional[float] = None


class FundSchemaCreate(BaseModel):
    fund_name: str


class FundSchemaUpdate(BaseModel):
    fund_name: Optional[str] = None
    stocks: list[StockSchema] | None = None


class StockSearchResult(BaseModel):
    symbol: str
    name: str
    exchange: str
    price: Optional[float] = None
    type: str


class StockSearchResponse(BaseModel):
    query: str
    results: list[StockSearchResult]
    count: int
