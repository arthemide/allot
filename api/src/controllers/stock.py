from fastapi import HTTPException
from loguru import logger

from src.models.pydantic.schema import (
    FundSchema,
    StockSchema,
)
from src.services.stock import StockService


class StockController:
    @staticmethod
    def add(fund_id: str, stock: StockSchema) -> FundSchema:
        """Add a stock to a fund"""
        logger.info(f"Adding stock {stock.symbol} to fund {fund_id}")
        fund = StockService.add(fund_id, stock)
        if not fund:
            raise HTTPException(
                status_code=404, detail=f"Fund with id {fund_id} not found"
            )
        return fund

    @staticmethod
    def update(fund_id: str, stock_id: str, stock: StockSchema) -> FundSchema:
        """Update a stock in a fund"""
        logger.info(f"Updating stock {stock_id} in fund {fund_id}")
        fund = StockService.update(fund_id, stock_id, stock)
        if not fund:
            raise HTTPException(
                status_code=404, detail=f"Fund {fund_id} or stock {stock_id} not found"
            )
        return fund

    @staticmethod
    def remove(fund_id: str, stock_id: str) -> FundSchema:
        """Remove a stock from a fund"""
        logger.info(f"Removing stock {stock_id} from fund {fund_id}")
        fund = StockService.remove(fund_id, stock_id)
        if not fund:
            raise HTTPException(
                status_code=404, detail=f"Fund {fund_id} or stock {stock_id} not found"
            )
        return fund
