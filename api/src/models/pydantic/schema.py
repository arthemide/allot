from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class StockSchema(BaseModel):
    id: Optional[str] = None
    symbol: str
    parts_number: float
    prum: float
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


class FundSchemaCreate(BaseModel):
    fund_name: str


class FundSchemaUpdate(BaseModel):
    fund_name: Optional[str] = None
    stocks: list[StockSchema] | None = None


class StockSearchResult(BaseModel):
    symbol: str
    name: str
    exchange: str
    type: str


class StockSearchResponse(BaseModel):
    query: str
    results: list[StockSearchResult]
    count: int
