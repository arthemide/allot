"""Market prices, straight off the Yahoo Finance JSON endpoints, with the
SQLite cache in front.

Also fronts the ticker search, so a symbol can be found by name instead of
guessing the exchange suffix (WPEA.PA, VWCE.DE, IUSN.DE, ETH-USD...).

Two endpoints carry everything:

    /v8/finance/chart/{symbol}   quote metadata *and* daily closes
    /v1/finance/search           ticker lookup by name

Neither is documented by Yahoo, and both fingerprint the TLS handshake: a
plain HTTP client is answered 429 no matter what User-Agent it sends, which is
why curl_cffi is used to present a real browser's handshake. That is also the
one piece yfinance was worth keeping -- the rest of it drags pandas and numpy
along, and neither has ever published an armv7 wheel, for any version. The
deployment target is a 32-bit Raspberry Pi.

Every call is wrapped: a failure degrades to a stale value or an empty list,
never to a 500.
"""

from __future__ import annotations

import logging
import threading
import time
from datetime import date, datetime, timedelta, timezone

from curl_cffi import requests

from src.databases import sqlite as db

logger = logging.getLogger(__name__)

EUR_USD_TICKER = "EURUSD=X"
CACHE_MAX_AGE_DAYS = 1

CHART_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
SEARCH_URL = "https://query1.finance.yahoo.com/v1/finance/search"

# Yahoo answers 429 to anything whose TLS handshake is not a browser's, so the
# User-Agent alone is not enough: `impersonate` is what actually gets through.
IMPERSONATE = "chrome"
TIMEOUT_SECONDS = 15

# One session per thread rather than one shared: the startup ticker check runs
# on its own thread alongside request handling, and a curl session is not
# documented as safe to share.
_local = threading.local()


def _session():
    session = getattr(_local, "session", None)
    if session is None:
        session = requests.Session(impersonate=IMPERSONATE, timeout=TIMEOUT_SECONDS)
        _local.session = session
    return session


# A single page draws positions, totals and the note, and each of those walks
# every asset. Without this, one page load is one network round-trip per asset
# per view. Quotes are delayed anyway, so a few minutes of staleness costs
# nothing.
QUOTE_TTL_SECONDS = 300
_quotes: dict[str, tuple[float, float | None]] = {}


def forget_quotes() -> None:
    """Drop the in-memory quote cache. Only useful to tests."""
    _quotes.clear()


def _chart(symbol: str, **params) -> dict | None:
    """One chart call, returning `result[0]` or None. Never raises."""
    try:
        response = _session().get(CHART_URL.format(symbol=symbol), params=params)
        response.raise_for_status()
        payload = response.json()
    except Exception as error:  # network, HTTP status, malformed JSON
        logger.warning("%s: chart fetch failed - %s", symbol, error)
        return None

    chart = (payload or {}).get("chart") or {}
    if chart.get("error"):
        logger.warning("%s: %s", symbol, chart["error"])
        return None
    results = chart.get("result") or []
    return results[0] if results else None


def _metadata(symbol: str) -> dict | None:
    result = _chart(symbol, range="1d", interval="1d")
    metadata = (result or {}).get("meta")
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


def _epoch(day: date) -> int:
    return int(datetime(day.year, day.month, day.day, tzinfo=timezone.utc).timestamp())


def _closes(result: dict) -> list[tuple[str, float]]:
    """Flatten a chart result into (ISO date, close) pairs.

    Adjusted closes are preferred, matching what yfinance returned before:
    its `history()` auto-adjusts for splits and dividends by default, and the
    stored cache must stay comparable across the change.

    Timestamps are UTC epochs; the exchange's own offset turns them back into
    the calendar day the session belongs to, which is the day the chart labels.
    """
    timestamps = result.get("timestamp") or []
    indicators = result.get("indicators") or {}
    adjusted = (indicators.get("adjclose") or [{}])[0].get("adjclose")
    raw = (indicators.get("quote") or [{}])[0].get("close")
    closes = adjusted or raw or []

    offset = (result.get("meta") or {}).get("gmtoffset") or 0

    points = []
    for stamp, close in zip(timestamps, closes):
        if stamp is None or close is None:  # holidays and half-sessions
            continue
        day = datetime.fromtimestamp(stamp + offset, tz=timezone.utc).date()
        points.append((day.isoformat(), float(close)))
    return points


def price_history(symbol: str, start: date, end: date | None = None) -> list[dict]:
    """Daily closes between `start` and `end`, cached in price_cache.

    The cache is refilled when it does not already span the requested window,
    so a chart redraw costs no network call.
    """
    end = end or date.today()
    cached = db.cached_prices(symbol)
    if cached and _covers(cached, start, end):
        return _within(cached, start, end)

    # A day of slack on each side absorbs the timezone edges: the window is
    # clipped exactly afterwards.
    result = _chart(
        symbol,
        period1=_epoch(start - timedelta(days=1)),
        period2=_epoch(end + timedelta(days=2)),
        interval="1d",
    )
    if result is None:
        # Fall back on whatever was cached, still clipped to the requested
        # window: a chart drawn from stale data must not silently span a
        # different range than the one asked for.
        return _within(cached, start, end)

    points = [
        (day, price)
        for day, price in _closes(result)
        if start.isoformat() <= day <= end.isoformat()
    ]
    if points:
        db.cache_prices(symbol, iter(points))
    return [{"date": d, "price": p} for d, p in points]


def _within(points: list[dict], start: date, end: date) -> list[dict]:
    return [p for p in points if start.isoformat() <= p["date"] <= end.isoformat()]


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
        response = _session().get(
            SEARCH_URL,
            params={"q": query, "quotesCount": limit, "newsCount": 0},
        )
        response.raise_for_status()
        quotes = (response.json() or {}).get("quotes") or []
    except Exception as error:
        logger.warning("search %r failed - %s", query, error)
        return []

    results = []
    for quote in quotes[:limit]:
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
