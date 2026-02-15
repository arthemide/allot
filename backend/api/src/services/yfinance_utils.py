"""
Yfinance utilities for stock data retrieval.

Provides functions to fetch stock prices, names, and search for symbols
using the yfinance library.
"""

import yfinance as yf
from loguru import logger


def _get_history_metadata(symbol: str) -> dict | None:
    """
    Get history metadata for a stock symbol.

    Args:
        symbol: Stock ticker symbol

    Returns:
        Dictionary with metadata or None if not found
    """
    logger.debug(f"Getting history metadata of {symbol}")
    stock_data = yf.Ticker(symbol)
    history_metadata = stock_data.get_history_metadata()
    if history_metadata is None:
        logger.error(f"{symbol}: No data found, symbol may be delisted")
        return None
    return history_metadata


def get_stock_price(symbol: str) -> float | None:
    """
    Get the current market price for a stock symbol.

    Args:
        symbol: Stock ticker symbol (e.g., "AAPL", "MSFT")

    Returns:
        Current price rounded to 2 decimals, or None if not found
    """
    logger.debug(f"Getting stock price of {symbol}")
    history_metadata = _get_history_metadata(symbol)
    if history_metadata is None:
        return None

    current_price = history_metadata.get("regularMarketPrice")
    logger.debug(f"Current price of '{symbol}' is {current_price}")
    return round(current_price, 2)


def get_long_name(symbol: str) -> str | None:
    """
    Get the long company name for a stock symbol.

    Args:
        symbol: Stock ticker symbol (e.g., "AAPL" -> "Apple Inc.")

    Returns:
        Company long name or None if not found
    """
    logger.debug(f"Getting long name of {symbol}")
    history_metadata = _get_history_metadata(symbol)
    if history_metadata is None:
        return None

    return history_metadata.get("longName")


def search_symbol(query: str, max_results: int = 10) -> list[dict]:
    """
    Search for stock symbols using yfinance.

    Args:
        query: The search query (company name, symbol, etc.)
        max_results: Maximum number of results to return (default: 10)

    Returns:
        List of dictionaries containing symbol information with keys:
            - symbol: Stock ticker symbol
            - name: Company name
            - exchange: Stock exchange
            - type: Security type (e.g., EQUITY, ETF)
            - price: Current market price
    """
    logger.debug(f"Searching for symbol: {query}")
    try:
        search_results = yf.Search(query)
        results = []

        for quote in search_results.quotes[:max_results]:
            history_metadata = _get_history_metadata(quote.get("symbol", ""))
            price = (
                history_metadata.get("regularMarketPrice") if history_metadata else 0.0
            )
            long_name = history_metadata.get("longName") if history_metadata else None
            short_name = history_metadata.get("shortName") if history_metadata else None
            name = long_name or short_name or "N/A"
            results.append(
                {
                    "symbol": quote.get("symbol", ""),
                    "name": name,
                    "exchange": quote.get("exchange", ""),
                    "type": quote.get("quoteType", ""),
                    "price": price,
                }
            )

        logger.debug(f"Found {len(results)} results for query: {query}")
        return results
    except Exception as e:
        logger.error(f"Error searching for symbol '{query}': {e}")
        return []
