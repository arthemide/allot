"""Market prices, via yfinance, with the SQLite cache in front.

An asset whose price_source is "manual" never reaches this module: callers must
check first. That is enforced by `current_price` raising on manual assets.
"""

from __future__ import annotations

import logging
from datetime import date, datetime, timedelta

import yfinance as yf

from src.databases import sqlite as db

logger = logging.getLogger(__name__)

EUR_USD_TICKER = "EURUSD=X"
CACHE_MAX_AGE_DAYS = 1


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
    """Latest market price, or None if the ticker does not answer."""
    metadata = _metadata(symbol)
    if metadata is None:
        return None
    price = metadata.get("regularMarketPrice")
    return round(price, 2) if price is not None else None


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
        return [p for p in cached if start.isoformat() <= p["date"] <= end.isoformat()]

    try:
        frame = yf.Ticker(symbol).history(
            start=start.isoformat(), end=(end + timedelta(days=1)).isoformat()
        )
    except Exception as error:
        logger.warning("%s: history fetch failed - %s", symbol, error)
        return cached

    points = [
        (index.date().isoformat(), float(row["Close"]))
        for index, row in frame.iterrows()
    ]
    if points:
        db.cache_prices(symbol, iter(points))
    return [{"date": d, "price": p} for d, p in points]


def _covers(cached: list[dict], start: date, end: date) -> bool:
    first = datetime.fromisoformat(cached[0]["date"]).date()
    last = datetime.fromisoformat(cached[-1]["date"]).date()
    if first > start:
        return False
    return (end - last).days <= CACHE_MAX_AGE_DAYS
