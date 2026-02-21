from typing import List

import yfinance as yf
from fastapi import APIRouter, HTTPException, Query
from loguru import logger

from src.models.pydantic.schema import (
    PricePoint,
    StockSearchResponse,
    StockSearchResult,
)
from src.services.yfinance_utils import search_symbol

router = APIRouter(prefix="/stocks", tags=["stocks"])


@router.get("/price-history", response_model=List[PricePoint])
async def get_price_history(
    symbol: str = Query(..., description="Asset symbol (yfinance format)"),
    start: str = Query(..., description="Start date YYYY-MM-DD"),
    end: str = Query(..., description="End date YYYY-MM-DD"),
):
    """
    Fetch daily close price history for a symbol via yfinance.
    Returns [] silently if the symbol is not recognized.
    """
    try:
        df = yf.download(symbol, start=start, end=end, interval="1d", progress=False)
        if df.empty:
            return []
        close = df["Close"]
        # Flatten MultiIndex columns if present
        if hasattr(close, "columns"):
            close = close.iloc[:, 0]
        result = [
            PricePoint(date=str(idx.date()), price=float(val))
            for idx, val in close.items()
            if val is not None
        ]
        return result
    except Exception as e:
        logger.warning(f"price-history failed for {symbol}: {e}")
        return []


@router.get("/search", response_model=StockSearchResponse)
async def search_stocks(
    q: str = Query(..., description="Search query for stock symbols or company names"),
    max_results: int = Query(
        10, ge=1, le=50, description="Maximum number of results to return"
    ),
):
    """
    Search for stock symbols by company name or ticker.

    Args:
        q: Search query string
        max_results: Maximum number of results (default: 10, max: 50)

    Returns:
        StockSearchResponse with matching stocks
    """
    logger.info(f"Searching for stocks with query: {q}")

    try:
        results = search_symbol(q, max_results=max_results)

        search_results = [StockSearchResult(**result) for result in results]

        return StockSearchResponse(
            query=q, results=search_results, count=len(search_results)
        )
    except Exception as e:
        logger.error(f"Error searching for stocks: {e}")
        raise HTTPException(
            status_code=500, detail=f"Error searching for stocks: {str(e)}"
        )
