"""Everything here exists so a page load is not one round-trip per asset."""

from datetime import date

import pytest

from src.services import prices

HISTORY = [
    {"date": "2026-01-10", "price": 10.0},
    {"date": "2026-02-10", "price": 11.0},
    {"date": "2026-03-10", "price": 12.0},
]


@pytest.fixture(autouse=True)
def clean_cache():
    prices.forget_quotes()
    yield
    prices.forget_quotes()


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


class TestPriceHistory:
    def test_a_covering_cache_is_served_clipped_to_the_window(self, mocker):
        # Given a cache spanning more than the requested window
        mocker.patch.object(prices.db, "cached_prices", return_value=HISTORY)
        mocker.patch.object(prices, "_covers", return_value=True)
        ticker = mocker.patch.object(prices.yf, "Ticker")
        # When a narrower window is asked for
        points = prices.price_history(
            "WPEA.PA", date(2026, 2, 1), date(2026, 2, 28)
        )
        # Then only that window comes back, without a network call
        assert [p["date"] for p in points] == ["2026-02-10"]
        ticker.assert_not_called()

    def test_a_failed_fetch_falls_back_on_the_same_window(self, mocker):
        # Given a stale cache and a provider that is down
        mocker.patch.object(prices.db, "cached_prices", return_value=HISTORY)
        mocker.patch.object(prices.yf, "Ticker", side_effect=RuntimeError("down"))
        # When the chart asks for one month
        points = prices.price_history(
            "WPEA.PA", date(2026, 2, 1), date(2026, 2, 28)
        )
        # Then the fallback is clipped like the nominal path, so the chart
        # never silently spans a different range than the one requested
        assert [p["date"] for p in points] == ["2026-02-10"]
