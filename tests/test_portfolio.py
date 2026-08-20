"""Manual assets must never reach the network."""

import pytest

from src.services import portfolio


@pytest.fixture
def exploding_prices(monkeypatch):
    """Any price lookup during the test is a failure."""

    def boom(*args, **kwargs):
        raise AssertionError("a manual asset must not trigger a price lookup")

    monkeypatch.setattr(portfolio.prices, "current_price", boom)
    monkeypatch.setattr(portfolio.prices, "price_history", boom)


def _manual_asset(**overrides):
    asset = {
        "symbol": "AFER",
        "label": "AFER life insurance",
        "envelope": "AFER",
        "currency": "EUR",
        "price_source": "manual",
        "base_quantity": 0.0,
        "base_prum": None,
        "manual_value": 4200.0,
    }
    return {**asset, **overrides}


class TestManualAsset:
    def test_position_uses_the_hand_entered_value(self, exploding_prices):
        # Given a manual asset worth 4200 entered by hand
        result = portfolio.position_of(_manual_asset())
        # Then its value is that number, with no PRUM and no quantity
        assert result["market_value"] == 4200.0
        assert result["invested"] == 4200.0
        assert result["prum"] is None
        assert result["quantity"] is None

    def test_missing_value_reads_as_zero(self, exploding_prices):
        result = portfolio.position_of(_manual_asset(manual_value=None))
        assert result["market_value"] == 0.0

    def test_chart_is_empty_and_offline(self, exploding_prices, monkeypatch):
        # Given the asset is manual
        monkeypatch.setattr(
            portfolio.db, "get_asset", lambda symbol: _manual_asset()
        )
        # When a chart is requested
        chart = portfolio.chart_data("AFER")
        # Then it comes back empty rather than hitting yfinance
        assert chart["prices"] == []
        assert chart["prum"] == []
