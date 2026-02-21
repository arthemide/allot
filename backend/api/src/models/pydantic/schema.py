from datetime import datetime

from pydantic import BaseModel


class StockSchema(BaseModel):
    id: str | None = None
    name: str | None
    symbol: str
    shares_number: float
    cost: float
    prum: float | None = None
    today_price: float | None = None
    market_value: float | None = None
    gain_loss: float | None = None
    gain_loss_percentage: float | None = None
    current_repartition: float
    target_repartition: float | None = None
    arbitration_threshold: float
    threshold_to_alert: float


class FundSchema(BaseModel):
    id: str | None = None
    fund_name: str
    stocks: list[StockSchema]
    created_at: datetime | None = None
    updated_at: datetime | None = None
    total_cost: float | None = None
    total_market_value: float | None = None
    total_gain_loss: float | None = None
    average_gain_loss_percentage: float | None = None


class FundSchemaCreate(BaseModel):
    fund_name: str


class FundSchemaUpdate(BaseModel):
    fund_name: str | None = None
    stocks: list[StockSchema] | None = None


class StockSearchResult(BaseModel):
    symbol: str
    name: str
    exchange: str
    price: float | None = None
    type: str


class StockSearchResponse(BaseModel):
    query: str
    results: list[StockSearchResult]
    count: int


class TransactionSchema(BaseModel):
    id: int
    asset_id: int
    asset_symbol: str
    asset_name: str | None
    transaction_type: str  # 'buy' | 'sell'
    timestamp: datetime
    quantity: float
    price: float
    total_cost: float
    order_id: str | None
    created_at: datetime


class PricePoint(BaseModel):
    date: str
    price: float
