"""Everything here exists so a page load is not one round-trip per asset.

The Yahoo endpoints are undocumented and unmocked elsewhere, so the shape of
their payloads is pinned here: if Yahoo moves a key, these tests are what says
so, rather than a chart quietly rendering empty.
"""

from datetime import date

import pytest

from src.services import prices

HISTORY = [
    {"date": "2026-01-10", "price": 10.0},
    {"date": "2026-02-10", "price": 11.0},
    {"date": "2026-03-10", "price": 12.0},
]

# Trimmed to the keys the code reads, otherwise verbatim from
# /v8/finance/chart/WPEA.PA. 1767830400 is 2026-01-08T00:00:00Z; Paris is
# UTC+1, so these sessions land on the 8th, 9th and 12th.
CHART_PAYLOAD = {
    "chart": {
        "error": None,
        "result": [
            {
                "meta": {
                    "currency": "EUR",
                    "symbol": "WPEA.PA",
                    "exchangeTimezoneName": "Europe/Paris",
                    "gmtoffset": 3600,
                    "regularMarketPrice": 5.678,
                    "longName": "Amundi PEA Monde",
                    "shortName": "AMUNDI PEA MONDE",
                },
                "timestamp": [1767830400, 1767916800, 1768176000],
                "indicators": {
                    "quote": [{"close": [5.10, 5.20, 5.30]}],
                    "adjclose": [{"adjclose": [5.11, 5.21, 5.31]}],
                },
            }
        ],
    }
}

SEARCH_PAYLOAD = {
    "quotes": [
        {
            "symbol": "WPEA.PA",
            "shortname": "AMUNDI PEA MONDE",
            "exchange": "PAR",
            "quoteType": "ETF",
        },
        {"symbol": "", "shortname": "junk row with no symbol"},
    ]
}


@pytest.fixture(autouse=True)
def clean_cache():
    prices.forget_quotes()
    yield
    prices.forget_quotes()


class _Response:
    """The two things the code asks of a response, and nothing else.

    Deliberately not a curl_cffi object: these tests pin how the payload is
    read, not which client fetched it.
    """

    def __init__(self, payload, status=200):
        self._payload = payload
        self.status_code = status

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")

    def json(self):
        return self._payload


def _response(payload, status=200):
    return _Response(payload, status)


def _patch_get(mocker, **kwargs):
    """Patch the per-thread session so no request leaves the test."""
    session = mocker.MagicMock()
    session.get = mocker.MagicMock(**kwargs)
    mocker.patch.object(prices, "_session", return_value=session)
    return session.get


class TestCurrentPrice:
    def test_the_provider_is_asked_once_per_symbol(self, mocker):
        # Given a ticker that answers
        metadata = mocker.patch.object(
            prices, "_metadata", return_value={"regularMarketPrice": 12.345}
        )
        # When the same price is read three times, as three views would
        results = [prices.current_price("WPEA.PA") for _ in range(3)]
        # Then the network was hit once and the price is rounded to the cent
        assert results == [12.35, 12.35, 12.35]
        assert metadata.call_count == 1

    def test_a_symbol_that_does_not_answer_is_not_retried(self, mocker):
        # Given a delisted or unknown symbol
        metadata = mocker.patch.object(prices, "_metadata", return_value=None)
        # When it is read twice
        assert prices.current_price("NOPE") is None
        assert prices.current_price("NOPE") is None
        # Then the miss was cached too, rather than paying for it every time
        assert metadata.call_count == 1

    def test_the_cache_expires(self, mocker):
        # Given a price read once, on a clock we control
        clock = mocker.patch.object(prices.time, "monotonic", return_value=0.0)
        mocker.patch.object(
            prices, "_metadata", return_value={"regularMarketPrice": 1.0}
        )
        assert prices.current_price("WPEA.PA") == 1.0
        # When the TTL has passed and the price has moved
        clock.return_value = prices.QUOTE_TTL_SECONDS + 1
        mocker.patch.object(
            prices, "_metadata", return_value={"regularMarketPrice": 2.0}
        )
        # Then the provider is asked again
        assert prices.current_price("WPEA.PA") == 2.0


class TestMetadata:
    def test_the_quote_metadata_is_read_off_the_chart_payload(self, mocker):
        # Given Yahoo answering a well-formed chart
        _patch_get(mocker, return_value=_response(CHART_PAYLOAD))
        # When the metadata is read
        metadata = prices._metadata("WPEA.PA")
        # Then it is the `meta` object, untouched
        assert metadata["regularMarketPrice"] == 5.678
        assert metadata["currency"] == "EUR"
        assert metadata["longName"] == "Amundi PEA Monde"

    def test_an_http_error_degrades_to_none(self, mocker):
        # Given Yahoo rate-limiting us, which it does readily
        _patch_get(mocker, return_value=_response({}, status=429))
        # When the metadata is read
        # Then the failure is absorbed rather than raised at the route
        assert prices._metadata("WPEA.PA") is None

    def test_an_error_carried_inside_a_200_degrades_to_none(self, mocker):
        # Given the payload Yahoo returns for an unknown symbol
        payload = {"chart": {"result": None, "error": {"code": "Not Found"}}}
        _patch_get(mocker, return_value=_response(payload))
        # When the metadata is read
        # Then a 200 carrying an error is treated as a miss, not as data
        assert prices._metadata("NOPE.XX") is None


class TestPriceHistory:
    def test_closes_are_flattened_and_dated_in_the_exchange_timezone(self, mocker):
        # Given an empty cache and Yahoo answering three sessions
        mocker.patch.object(prices.db, "cached_prices", return_value=[])
        cache = mocker.patch.object(prices.db, "cache_prices")
        _patch_get(mocker, return_value=_response(CHART_PAYLOAD))
        # When a window covering them is asked for
        points = prices.price_history("WPEA.PA", date(2026, 1, 1), date(2026, 1, 31))
        # Then the adjusted closes come back, dated in Paris time, and cached.
        # Adjusted rather than raw: yfinance auto-adjusted by default, so the
        # stored history stays comparable across the switch.
        assert points == [
            {"date": "2026-01-08", "price": 5.11},
            {"date": "2026-01-09", "price": 5.21},
            {"date": "2026-01-12", "price": 5.31},
        ]
        cache.assert_called_once()

    def test_raw_closes_are_used_when_there_is_no_adjusted_series(self, mocker):
        # Given a payload without an adjclose block, as currencies return
        payload = {"chart": {"result": [dict(CHART_PAYLOAD["chart"]["result"][0])]}}
        payload["chart"]["result"][0]["indicators"] = {
            "quote": [{"close": [5.10, 5.20, 5.30]}]
        }
        mocker.patch.object(prices.db, "cached_prices", return_value=[])
        mocker.patch.object(prices.db, "cache_prices")
        _patch_get(mocker, return_value=_response(payload))
        # When the history is read
        points = prices.price_history("EURUSD=X", date(2026, 1, 1), date(2026, 1, 31))
        # Then it falls back on the raw closes rather than returning nothing
        assert [p["price"] for p in points] == [5.10, 5.20, 5.30]

    def test_gaps_in_the_series_are_dropped(self, mocker):
        # Given a session Yahoo has no close for, which it reports as null
        payload = {"chart": {"result": [dict(CHART_PAYLOAD["chart"]["result"][0])]}}
        payload["chart"]["result"][0]["indicators"] = {
            "adjclose": [{"adjclose": [5.11, None, 5.31]}]
        }
        mocker.patch.object(prices.db, "cached_prices", return_value=[])
        mocker.patch.object(prices.db, "cache_prices")
        _patch_get(mocker, return_value=_response(payload))
        # When the history is read
        points = prices.price_history("WPEA.PA", date(2026, 1, 1), date(2026, 1, 31))
        # Then the hole is skipped instead of becoming a zero on the chart
        assert [p["date"] for p in points] == ["2026-01-08", "2026-01-12"]

    def test_points_outside_the_window_are_clipped(self, mocker):
        # Given a fetch that overshoots, as the day of slack on each side does
        mocker.patch.object(prices.db, "cached_prices", return_value=[])
        mocker.patch.object(prices.db, "cache_prices")
        _patch_get(mocker, return_value=_response(CHART_PAYLOAD))
        # When a window narrower than the payload is asked for
        points = prices.price_history("WPEA.PA", date(2026, 1, 9), date(2026, 1, 9))
        # Then only the requested days survive
        assert [p["date"] for p in points] == ["2026-01-09"]

    def test_a_covering_cache_is_served_clipped_to_the_window(self, mocker):
        # Given a cache spanning more than the requested window
        mocker.patch.object(prices.db, "cached_prices", return_value=HISTORY)
        mocker.patch.object(prices, "_covers", return_value=True)
        get = _patch_get(mocker)
        # When a narrower window is asked for
        points = prices.price_history("WPEA.PA", date(2026, 2, 1), date(2026, 2, 28))
        # Then only that window comes back, without a network call
        assert [p["date"] for p in points] == ["2026-02-10"]
        get.assert_not_called()

    def test_a_failed_fetch_falls_back_on_the_same_window(self, mocker):
        # Given a stale cache and a provider that is down
        mocker.patch.object(prices.db, "cached_prices", return_value=HISTORY)
        _patch_get(mocker, side_effect=ConnectionError("down"))
        # When the chart asks for one month
        points = prices.price_history("WPEA.PA", date(2026, 2, 1), date(2026, 2, 28))
        # Then the fallback is clipped like the nominal path, so the chart
        # never silently spans a different range than the one requested
        assert [p["date"] for p in points] == ["2026-02-10"]


class TestSearch:
    def test_hits_are_resolved_against_their_metadata(self, mocker):
        # Given a search hit whose metadata answers
        _patch_get(mocker, return_value=_response(SEARCH_PAYLOAD))
        mocker.patch.object(
            prices,
            "_metadata",
            return_value=CHART_PAYLOAD["chart"]["result"][0]["meta"],
        )
        # When the ticker is looked up by name
        results = prices.search("amundi pea")
        # Then the row carries the resolved label, currency and price, and the
        # payload's empty-symbol row is dropped rather than shown
        assert results == [
            {
                "symbol": "WPEA.PA",
                "label": "Amundi PEA Monde",
                "exchange": "PAR",
                "type": "ETF",
                "currency": "EUR",
                "price": 5.68,
            }
        ]

    def test_a_symbol_that_does_not_answer_is_kept_with_a_null_price(self, mocker):
        # Given a hit whose metadata cannot be resolved
        _patch_get(mocker, return_value=_response(SEARCH_PAYLOAD))
        mocker.patch.object(prices, "_metadata", return_value=None)
        # When the ticker is looked up
        results = prices.search("amundi pea")
        # Then it is still offered, with the search payload's own label: seeing
        # a dead symbol is exactly what tells the user not to pick it
        assert results[0]["symbol"] == "WPEA.PA"
        assert results[0]["label"] == "AMUNDI PEA MONDE"
        assert results[0]["price"] is None
        assert results[0]["currency"] is None

    def test_a_failed_search_returns_nothing(self, mocker):
        # Given Yahoo refusing the search
        _patch_get(mocker, return_value=_response({}, status=429))
        # When a query is run
        # Then it degrades to an empty list rather than raising
        assert prices.search("anything") == []
