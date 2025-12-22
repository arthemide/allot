from typing import List

from fastapi import HTTPException
from loguru import logger

from src.models.pydantic.schema import (
    FundSchema,
    FundSchemaUpdate,
)
from src.services.fund import FundService


class FundController:
    """Controller for Fund endpoints"""

    @staticmethod
    def get_all_funds() -> List[FundSchema]:
        """Get all fund configurations"""
        logger.info("Getting all fund configurations")
        return FundService.get_all()

    @staticmethod
    def get_fund(fund_id: str) -> FundSchema:
        """Get a single fund configuration by ID"""
        logger.info(f"Getting fund configuration {fund_id}")
        fund = FundService.get_by_id(fund_id)
        if not fund:
            raise HTTPException(
                status_code=404, detail=f"Fund with id {fund_id} not found"
            )
        return fund

    @staticmethod
    def create(fund_name: str) -> FundSchema:
        """Create a new fund configuration"""
        logger.info(f"Creating fund configuration: {fund_name}")
        try:
            return FundService.create(fund_name)
        except Exception as e:
            logger.error(f"Error creating fund: {e}")
            raise HTTPException(
                status_code=500, detail=f"Error creating fund: {str(e)}"
            )

    @staticmethod
    def update(fund_id: str, updates: FundSchemaUpdate) -> FundSchema:
        """Update an existing fund configuration"""
        logger.info(f"Updating fund configuration {fund_id}")
        fund = FundService.update(fund_id, updates)
        if not fund:
            raise HTTPException(
                status_code=404, detail=f"Fund with id {fund_id} not found"
            )
        return fund

    @staticmethod
    def delete(fund_id: str) -> dict:
        """Delete a fund configuration"""
        logger.info(f"Deleting fund configuration {fund_id}")
        success = FundService.delete(fund_id)
        if not success:
            raise HTTPException(
                status_code=404, detail=f"Fund with id {fund_id} not found"
            )
        return {"success": True, "message": f"Fund {fund_id} deleted successfully"}
