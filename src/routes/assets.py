"""Asset and chart endpoints."""

from fastapi import APIRouter, HTTPException, status

from src.databases import sqlite as db
from src.models.schema import (
    ActualQuantity,
    Chart,
    ManualValue,
    Position,
    Simulation,
    SimulationRequest,
)
from src.services import portfolio

router = APIRouter(prefix="/assets", tags=["assets"])


@router.get("", response_model=list[Position])
def list_assets():
    """Every tracked asset with its recomputed position."""
    return portfolio.all_positions()


@router.get("/{symbol}", response_model=Position)
def get_asset(symbol: str):
    asset = db.get_asset(symbol)
    if asset is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Unknown asset")
    return portfolio.position_of(asset)


@router.get("/{symbol}/chart", response_model=Chart)
def get_chart(symbol: str):
    """Price history, transaction markers and the step PRUM curve."""
    if db.get_asset(symbol) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Unknown asset")
    return portfolio.chart_data(symbol)


@router.put("/{symbol}/manual-value", response_model=Position)
def set_manual_value(symbol: str, payload: ManualValue):
    """Set the hand-entered value of an asset that has no ticker."""
    asset = db.get_asset(symbol)
    if asset is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Unknown asset")
    if asset["price_source"] != "manual":
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, "Asset is priced from yfinance"
        )
    db.set_manual_value(symbol, payload.value)
    return portfolio.position_of(db.get_asset(symbol))


@router.post("/{symbol}/simulate", response_model=Simulation)
def simulate(symbol: str, payload: SimulationRequest):
    """What a buy would do to the PRUM, and what a target PRUM would cost."""
    if db.get_asset(symbol) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Unknown asset")
    try:
        return portfolio.simulate(
            symbol, payload.amount, payload.fees, payload.target_prum
        )
    except ValueError as error:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(error)) from error


@router.put("/{symbol}/actual-quantity", response_model=Position)
def set_actual_quantity(symbol: str, payload: ActualQuantity):
    """Record the quantity actually held on the platform, for comparison only."""
    if db.get_asset(symbol) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Unknown asset")
    db.set_actual_quantity(symbol, payload.quantity)
    return portfolio.position_of(db.get_asset(symbol))
