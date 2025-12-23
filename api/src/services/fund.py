from typing import List, Optional

from src.models.pydantic.schema import (
    FundSchema,
    FundSchemaUpdate,
)
from src.repositories.fund import FundRepository
from src.repositories.stock import StockRepository
from src.services.utils import fund_table_to_pydantic


class FundService:
    """Service for Fund business logic"""

    @staticmethod
    def get_all() -> List[FundSchema]:
        """Get all fund configurations"""
        funds = FundRepository.get_all()
        return [fund_table_to_pydantic(fund) for fund in funds]

    @staticmethod
    def get_by_id(fund_id: str) -> Optional[FundSchema]:
        """Get a single fund configuration"""
        fund = FundRepository.get_by_id(fund_id)
        return fund_table_to_pydantic(fund) if fund else None

    @staticmethod
    def create(fund_name: str) -> FundSchema:
        """Create a new fund configuration"""
        fund = FundRepository.create(fund_name)
        return fund_table_to_pydantic(fund)

    @staticmethod
    def update(fund_id: str, updates: FundSchemaUpdate) -> Optional[FundSchema]:
        """Update an existing fund configuration"""

        if updates.stocks is not None:
            fund = FundRepository.get_by_id(fund_id)
            if not fund:
                return None

            # Remove all existing stocks
            for stock in list(fund.stocks):
                StockRepository.remove(fund_id, stock.id)

            # Add new stocks
            for stock in updates.stocks:
                stock_data = {
                    "symbol": stock.symbol,
                    "shares_number": stock.shares_number,
                    "prum": stock.prum,
                    "current_repartition": stock.current_repartition,
                    "target_repartition": stock.target_repartition,
                    "arbitration_threshold": stock.arbitration_threshold,
                    "threshold_to_alert": stock.threshold_to_alert,
                }
                StockRepository.add(fund_id, stock_data)

        # Update fund name if provided
        if updates.fund_name is not None:
            fund = FundRepository.update(fund_id, updates.fund_name)
        else:
            fund = FundRepository.get_by_id(fund_id)

        return fund_table_to_pydantic(fund) if fund else None

    @staticmethod
    def delete(fund_id: str) -> bool:
        """Delete a fund configuration"""
        return FundRepository.delete(fund_id)
