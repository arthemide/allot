from typing import List

from fastapi import APIRouter, HTTPException, status

from src.models.pydantic.schema import (
    FundSchema,
    FundSchemaCreate,
    FundSchemaUpdate,
    StockSchema,
)
from src.services.fund import FundService
from src.services.stock import StockService

# Fund configuration routes
router = APIRouter(prefix="/funds", tags=["funds"])


@router.get("", response_model=List[FundSchema])
def get_all_funds():
    """Get all fund configurations"""
    return FundService.get_all()


@router.get("/{fund_id}", response_model=FundSchema)
def get_fund(fund_id: str):
    """Get a single fund by ID"""
    fund = FundService.get_by_id(fund_id)
    if fund is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Fund not found"
        )
    return fund


@router.post("", response_model=FundSchema, status_code=status.HTTP_201_CREATED)
def create_fund(fund: FundSchemaCreate):
    """Create a new fund"""
    return FundService.create(fund.fund_name)


@router.put("/{fund_id}", response_model=FundSchema)
def update_fund(fund_id: str, updates: FundSchemaUpdate):
    """Update an existing fund"""
    fund = FundService.update(fund_id, updates)
    if fund is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Fund not found"
        )
    return fund


@router.delete("/{fund_id}")
def delete_fund(fund_id: str):
    """Delete a fund"""
    return FundService.delete(fund_id)


@router.post("/{fund_id}/stocks", response_model=FundSchema)
def add_stock(fund_id: str, stock: StockSchema):
    """Add a stock to a fund"""
    result = StockService.add(fund_id, stock)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Fund not found"
        )
    return result


@router.put("/{fund_id}/stocks/{stock_id}", response_model=FundSchema)
def update_stock(fund_id: str, stock_id: str, stock: StockSchema):
    """Update a stock in a fund"""
    result = StockService.update(fund_id, stock_id, stock)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Fund or stock not found"
        )
    return result


@router.delete("/{fund_id}/stocks/{stock_id}", response_model=FundSchema)
def remove_stock(fund_id: str, stock_id: str):
    """Remove a stock from a fund"""
    result = StockService.remove(fund_id, stock_id)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Fund or stock not found"
        )
    return result
