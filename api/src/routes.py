from fastapi import APIRouter, HTTPException, Query
from loguru import logger

from src.models import StockSearchResponse, StockSearchResult
from src.stock import Stock

router = APIRouter(prefix="/stocks", tags=["debug"])


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
        results = Stock.search_symbol(q, max_results=max_results)

        search_results = [StockSearchResult(**result) for result in results]

        return StockSearchResponse(
            query=q, results=search_results, count=len(search_results)
        )
    except Exception as e:
        logger.error(f"Error searching for stocks: {e}")
        raise HTTPException(
            status_code=500, detail=f"Error searching for stocks: {str(e)}"
        )
