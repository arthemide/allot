from src.databases.fund import FundRepository
from src.databases.stock import StockRepository
from src.models.pydantic.schema import (
    FundSchema,
    StockSchema,
)
from src.services.utils import fund_table_to_pydantic
from src.services.yfinance_utils import get_long_name


class StockService:
    @staticmethod
    def add(fund_id: str, stock: StockSchema) -> FundSchema | None:
        """Add a stock to a fund"""
        fund = FundRepository.get_by_id(fund_id)
        if not fund:
            return None
        if stock.name is None:
            stock.name = get_long_name(stock.symbol)
        fund = StockRepository.add(fund_id, stock)
        return fund_table_to_pydantic(fund) if fund else None

    @staticmethod
    def update(fund_id: str, stock_id: str, stock: StockSchema) -> FundSchema | None:
        """Update a stock in a fund"""
        fund = StockRepository.update(fund_id, stock_id, stock)
        return fund_table_to_pydantic(fund) if fund else None

    @staticmethod
    def remove(fund_id: str, stock_id: str) -> FundSchema | None:
        """Remove a stock from a fund"""
        fund = StockRepository.remove(fund_id, stock_id)
        return fund_table_to_pydantic(fund) if fund else None
