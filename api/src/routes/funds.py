from typing import List

from fastapi import APIRouter

from src.controllers.fund import FundController
from src.controllers.stock import StockController
from src.models.pydantic.schema import (
    FundSchema,
    FundSchemaCreate,
    FundSchemaUpdate,
    StockSchema,
)

# Fund configuration routes
router = APIRouter(prefix="/funds", tags=["funds"])


@router.get("", response_model=List[FundSchema])
def get_all_funds():
    """Get all fund configurations"""
    return FundController.get_all_funds()


@router.get("/{fund_id}", response_model=FundSchema)
def get_fund(fund_id: str):
    """Get a single fund by ID"""
    return FundController.get_fund(fund_id)


@router.post("", response_model=FundSchema, status_code=201)
def create_fund(fund: FundSchemaCreate):
    """Create a new fund"""
    return FundController.create(fund.fund_name)


@router.put("/{fund_id}", response_model=FundSchema)
def update_fund(fund_id: str, updates: FundSchemaUpdate):
    """Update an existing fund"""
    return FundController.update(fund_id, updates)


@router.delete("/{fund_id}")
def delete_fund(fund_id: str):
    """Delete a fund"""
    return FundController.delete(fund_id)


@router.post("/{fund_id}/stocks", response_model=FundSchema)
def add_stock(fund_id: str, stock: StockSchema):
    """Add a stock to a fund"""
    return StockController.add(fund_id, stock)


@router.put("/{fund_id}/stocks/{stock_id}", response_model=FundSchema)
def update_stock(fund_id: str, stock_id: str, stock: StockSchema):
    """Update a stock in a fund"""
    return StockController.update(fund_id, stock_id, stock)


@router.delete("/{fund_id}/stocks/{stock_id}", response_model=FundSchema)
def remove_stock(fund_id: str, stock_id: str):
    """Remove a stock from a fund"""
    return StockController.remove(fund_id, stock_id)
