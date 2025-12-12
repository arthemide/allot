from pydantic import BaseModel


class StockConfig(BaseModel):
    symbol: str
    parts_number: float
    prum: float
    current_repartition: float
    target_repartition: float
    arbitration_threshold: float
    threshold_to_alert: float


class FundConfig(BaseModel):
    fund_name: str
    stocks: list[StockConfig]


class StockSearchResult(BaseModel):
    symbol: str
    name: str
    exchange: str
    type: str


class StockSearchResponse(BaseModel):
    query: str
    results: list[StockSearchResult]
    count: int
