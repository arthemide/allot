from typing import List

from src.databases.fund import FundRepository
from src.databases.stock import StockRepository
from src.models.pydantic.schema import (
    FundSchema,
    FundSchemaUpdate,
)
from src.services.utils import fund_table_to_pydantic


class FundService:
    """Service for Fund business logic"""

    @staticmethod
    def get_all() -> List[FundSchema]:
        """Get all fund configurations"""
        funds = FundRepository.get_all()
        return [fund_table_to_pydantic(fund) for fund in funds]

    @staticmethod
    def get_by_id(fund_id: str) -> FundSchema | None:
        """Get a single fund configuration"""
        fund = FundRepository.get_by_id(fund_id)
        return fund_table_to_pydantic(fund) if fund else None

    @staticmethod
    def create(fund_name: str) -> FundSchema:
        """Create a new fund configuration"""
        fund = FundRepository.create(fund_name)
        return fund_table_to_pydantic(fund)

    @staticmethod
    def update(fund_id: str, updates: FundSchemaUpdate) -> FundSchema | None:
        """Update an existing fund configuration"""

        if updates.stocks:
            fund = FundRepository.get_by_id(fund_id)
            if not fund:
                return None

            # Remove all existing assets
            for asset in list(fund.assets):
                StockRepository.remove(fund_id, asset.id)

            # Add new stocks
            for stock in updates.stocks:
                stock_data = {
                    "symbol": stock.symbol,
                    "shares_number": stock.shares_number,
                    "cost": stock.cost,
                    "current_repartition": stock.current_repartition,
                    "target_repartition": stock.target_repartition,
                    "arbitration_threshold": stock.arbitration_threshold,
                    "threshold_to_alert": stock.threshold_to_alert,
                }
                StockRepository.add(fund_id, stock_data)

        # Update fund name if provided
        if updates.fund_name:
            fund = FundRepository.update(fund_id, updates.fund_name)
        else:
            fund = FundRepository.get_by_id(fund_id)

        return fund_table_to_pydantic(fund) if fund else None

    @staticmethod
    def delete(fund_id: str) -> bool:
        """Delete a fund configuration"""
        return FundRepository.delete(fund_id)
