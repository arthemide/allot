"""Market prices, via yfinance, with the SQLite cache in front.

Also fronts the ticker search, so a symbol can be found by name instead of
guessing the exchange suffix (WPEA.PA, VWCE.DE, IUSN.DE, ETH-USD...).
"""

from __future__ import annotations

import logging
import time
from datetime import date, datetime, timedelta

import yfinance as yf

from src.databases import sqlite as db

logger = logging.getLogger(__name__)

EUR_USD_TICKER = "EURUSD=X"
CACHE_MAX_AGE_DAYS = 1

# A single page draws positions, totals and the note, and each of those walks
# every asset. Without this, one page load is one network round-trip per asset
# per view. Quotes are delayed anyway, so a few minutes of staleness costs
# nothing.
QUOTE_TTL_SECONDS = 300
_quotes: dict[str, tuple[float, float | None]] = {}


def forget_quotes() -> None:
    """Drop the in-memory quote cache. Only useful to tests."""
    _quotes.clear()


def _metadata(symbol: str) -> dict | None:
    try:
        metadata = yf.Ticker(symbol).get_history_metadata()
    except Exception as error:  # yfinance raises a wide range of exceptions
        logger.warning("%s: metadata fetch failed - %s", symbol, error)
        return None
    if not metadata:
        logger.warning("%s: no data, symbol may be delisted or unsupported", symbol)
        return None
    return metadata


def current_price(symbol: str) -> float | None:
    """Latest market price, or None if the ticker does not answer.

    Memoised for QUOTE_TTL_SECONDS, misses included: a symbol that does not
    answer must not be retried once per asset per request.
    """
    cached = _quotes.get(symbol)
    if cached is not None and time.monotonic() - cached[0] < QUOTE_TTL_SECONDS:
        return cached[1]

    metadata = _metadata(symbol)
    price = metadata.get("regularMarketPrice") if metadata else None
    price = round(price, 2) if price is not None else None
    _quotes[symbol] = (time.monotonic(), price)
    return price


def check_tickers(symbols: list[str]) -> list[str]:
    """Return the symbols that do not answer. Never raises: startup must not block."""
    failing = []
    for symbol in symbols:
        if current_price(symbol) is None:
            failing.append(symbol)
    return failing


def eur_usd_rate() -> float | None:
    """USD per EUR, used only to total envelopes and net worth."""
    return current_price(EUR_USD_TICKER)


def price_history(symbol: str, start: date, end: date | None = None) -> list[dict]:
    """Daily closes between `start` and `end`, cached in price_cache.

    The cache is refilled when it does not already span the requested window,
    so a chart redraw costs no network call.
    """
    end = end or date.today()
    cached = db.cached_prices(symbol)
    if cached and _covers(cached, start, end):
        return _within(cached, start, end)

    try:
        frame = yf.Ticker(symbol).history(
            start=start.isoformat(), end=(end + timedelta(days=1)).isoformat()
        )
    except Exception as error:
        # Fall back on whatever was cached, still clipped to the requested
        # window: a chart drawn from stale data must not silently span a
        # different range than the one asked for.
        logger.warning("%s: history fetch failed - %s", symbol, error)
        return _within(cached, start, end)

    points = [
        (index.date().isoformat(), float(row["Close"]))
        for index, row in frame.iterrows()
    ]
    if points:
        db.cache_prices(symbol, iter(points))
    return [{"date": d, "price": p} for d, p in points]


def _within(points: list[dict], start: date, end: date) -> list[dict]:
    return [
        p for p in points if start.isoformat() <= p["date"] <= end.isoformat()
    ]


def _covers(cached: list[dict], start: date, end: date) -> bool:
    first = datetime.fromisoformat(cached[0]["date"]).date()
    last = datetime.fromisoformat(cached[-1]["date"]).date()
    if first > start:
        return False
    return (end - last).days <= CACHE_MAX_AGE_DAYS


def search(query: str, limit: int = 10) -> list[dict]:
    """Look a ticker up by name or symbol.

    Exchange suffixes are the whole difficulty here, so each hit is resolved
    against its metadata: a symbol that does not answer is returned with a null
    price rather than hidden, because that is exactly what the user needs to
    see before picking one.
    """
    try:
        quotes = yf.Search(query).quotes[:limit]
    except Exception as error:
        logger.warning("search %r failed - %s", query, error)
        return []

    results = []
    for quote in quotes:
        symbol = quote.get("symbol", "")
        if not symbol:
            continue
        metadata = _metadata(symbol)
        price = metadata.get("regularMarketPrice") if metadata else None
        results.append(
            {
                "symbol": symbol,
                "label": (
                    (metadata or {}).get("longName")
                    or (metadata or {}).get("shortName")
                    or quote.get("shortname")
                    or symbol
                ),
                "exchange": quote.get("exchange", ""),
                "type": quote.get("quoteType", ""),
                "currency": ((metadata or {}).get("currency") or "").upper() or None,
                "price": round(price, 2) if price is not None else None,
            }
        )
    return results
