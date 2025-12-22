from typing import Optional

from src.models.pydantic.schema import (
    FundSchema,
    StockSchema,
)
from src.repositories.fund import FundRepository
from src.repositories.stock import StockRepository
from src.services.utils import fund_table_to_pydantic


class StockService:
    @staticmethod
    def add(fund_id: str, stock: StockSchema) -> Optional[FundSchema]:
        """Add a stock to a fund"""
        fund = FundRepository.get_by_id(fund_id)
        if not fund:
            return None
        fund = StockRepository.add(fund_id, stock)
        return fund_table_to_pydantic(fund) if fund else None

    @staticmethod
    def update(fund_id: str, stock_id: str, stock: StockSchema) -> Optional[FundSchema]:
        """Update a stock in a fund"""
        fund = StockRepository.update(fund_id, stock_id, stock)
        return fund_table_to_pydantic(fund) if fund else None

    @staticmethod
    def remove(fund_id: str, stock_id: str) -> Optional[FundSchema]:
        """Remove a stock from a fund"""
        fund = StockRepository.remove(fund_id, stock_id)
        return fund_table_to_pydantic(fund) if fund else None
