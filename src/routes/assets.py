"""Asset, chart and ticker search endpoints."""

from fastapi import APIRouter, HTTPException, status

from src.databases import sqlite as db
from src.models.schema import (
    AssetCreate,
    AssetUpdate,
    Chart,
    OpeningPosition,
    Position,
    SearchHit,
    Summary,
)
from src.services import portfolio, prices

router = APIRouter(prefix="/assets", tags=["assets"])


@router.get("", response_model=list[Position])
def list_assets():
    """Every tracked asset with its recomputed position."""
    return portfolio.all_positions()


@router.post("", response_model=Position, status_code=status.HTTP_201_CREATED)
def create_asset(payload: AssetCreate):
    """Add an asset, normally picked from the ticker search."""
    existing = db.get_asset(payload.symbol)
    if existing is not None:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"{payload.symbol} is already tracked, in envelope "
            f"{existing['envelope']}. Change its envelope from the * page "
            f"instead of adding it again.",
        )
    if db.get_envelope(payload.envelope) is None:
        db.upsert_envelope(payload.envelope, 0.0)
    db.add_asset(
        payload.symbol,
        payload.label,
        payload.envelope,
        payload.currency,
        payload.weight,
    )
    return portfolio.position_of(db.get_asset(payload.symbol))


@router.get("/search", response_model=list[SearchHit])
def search_tickers(q: str, limit: int = 10):
    """Find a ticker by name, so the exchange suffix does not have to be guessed."""
    return prices.search(q, limit)


@router.get("/summary", response_model=Summary)
def get_summary():
    """Totals across every asset, converted to EUR."""
    return portfolio.summary()


@router.get("/{symbol}", response_model=Position)
def get_asset(symbol: str):
    asset = db.get_asset(symbol)
    if asset is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"No asset named {symbol}")
    return portfolio.position_of(asset)


@router.put("/{symbol}", response_model=Position)
def update_asset(symbol: str, payload: AssetUpdate):
    """Change the label, the envelope or the weight inside the envelope."""
    if db.get_asset(symbol) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"No asset named {symbol}")
    if db.get_envelope(payload.envelope) is None:
        db.upsert_envelope(payload.envelope, 0.0)
    db.update_asset(symbol, payload.label, payload.envelope, payload.weight)
    db.prune_empty_envelopes()
    return portfolio.position_of(db.get_asset(symbol))


@router.delete("/{symbol}", status_code=status.HTTP_204_NO_CONTENT)
def delete_asset(symbol: str):
    """Deletes the asset and its transactions."""
    if db.get_asset(symbol) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"No asset named {symbol}")
    db.delete_asset(symbol)
    db.prune_empty_envelopes()


@router.put("/{symbol}/opening", response_model=Position)
def set_opening_position(symbol: str, payload: OpeningPosition):
    """Set the holding that predates tracking, for a line with no history.

    A statement gives units held and total paid; the PRUM follows from those.
    """
    if db.get_asset(symbol) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"No asset named {symbol}")
    if payload.quantity > 0 and not payload.invested:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "A quantity needs the amount invested, otherwise there is no PRUM "
            "to compute. Leave the quantity at 0 to clear the opening position.",
        )
    db.set_opening_position(symbol, payload.quantity, payload.invested)
    return portfolio.position_of(db.get_asset(symbol))


@router.get("/{symbol}/chart", response_model=Chart)
def get_chart(symbol: str, window: str = portfolio.DEFAULT_RANGE):
    """Price history, transaction markers and the step PRUM curve.

    `window` is "tx" (a quarter before the first transaction) or one of
    "1y", "3y", "5y", "max".
    """
    if db.get_asset(symbol) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"No asset named {symbol}")
    return portfolio.chart_data(symbol, window)
