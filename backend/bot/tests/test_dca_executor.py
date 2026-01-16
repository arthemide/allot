"""
Simple tests for DCA executor decision logic.
Focus on the critical buy/skip decisions without overengineering.
"""
import pytest
from decimal import Decimal

from dca.dca_executor import DCAExecutor
from tests.conftest import create_kline


@pytest.fixture
def dca_config(mocker):
    """Create test DCA config using pytest-mock."""
    config = mocker.Mock()
    config.dca = mocker.Mock(
        symbol="ETHUSDC",
        base_asset="ETH",
        quote_asset="USDC",
        amount_usdc=30.0,
        base_prum=None,
        base_quantity=0.0
    )
    return config


class TestDCADecisionLogic:
    """Test when DCA should buy vs skip."""

    def test_should_skip_when_two_positive_periods_and_price_above_prum(
        self, mocker, mock_binance_client, mock_purchase_tracker, dca_config
    ):
        """Should SKIP if both periods positive AND price > PRUM."""
        # Patch PurchaseTracker to prevent DB connection
        mocker.patch("dca.dca_executor.PurchaseTracker")

        # Given: 2 positive periods, price at 3100, PRUM at 2000
        mock_binance_client.get_symbol_price.return_value = Decimal("3100.0")
        mock_binance_client.get_klines.return_value = [
            create_kline(open_price=2900, close_price=3000),  # Positive
            create_kline(open_price=3000, close_price=3050),  # Positive
            create_kline(open_price=3050, close_price=3100),  # Current (incomplete)
        ]
        mock_purchase_tracker.calculate_prum.return_value = Decimal("2000.0")

        executor = DCAExecutor(mock_binance_client, dca_config)
        executor.tracker = mock_purchase_tracker

        # When
        should_execute, reason = executor.should_execute_purchase()

        # Then: Should skip (bullish + price above PRUM)
        assert should_execute is False
        assert "skip" in reason.lower() or "bullish" in reason.lower()

    def test_should_buy_when_one_negative_period(
        self, mocker, mock_binance_client, mock_purchase_tracker, dca_config
    ):
        """Should BUY if at least one period is negative."""
        # Patch PurchaseTracker to prevent DB connection
        mocker.patch("dca.dca_executor.PurchaseTracker")

        # Given: 1 positive, 1 negative period
        mock_binance_client.get_symbol_price.return_value = Decimal("3100.0")
        mock_binance_client.get_klines.return_value = [
            create_kline(open_price=3200, close_price=3000),  # Negative
            create_kline(open_price=3000, close_price=3050),  # Positive
            create_kline(open_price=3050, close_price=3100),  # Current
        ]
        mock_purchase_tracker.calculate_prum.return_value = Decimal("2000.0")

        executor = DCAExecutor(mock_binance_client, dca_config)
        executor.tracker = mock_purchase_tracker

        # When
        should_execute, reason = executor.should_execute_purchase()

        # Then: Should buy
        assert should_execute is True

    def test_should_buy_when_price_below_prum(
        self, mocker, mock_binance_client, mock_purchase_tracker, dca_config
    ):
        """Should BUY if price is below or equal to PRUM, even with positive periods."""
        # Patch PurchaseTracker to prevent DB connection
        mocker.patch("dca.dca_executor.PurchaseTracker")

        # Given: 2 positive periods BUT price near PRUM
        mock_binance_client.get_symbol_price.return_value = Decimal("2000.0")
        mock_binance_client.get_klines.return_value = [
            create_kline(open_price=2000, close_price=2100),  # Positive
            create_kline(open_price=2100, close_price=2200),  # Positive
            create_kline(open_price=2200, close_price=2000),  # Current
        ]
        mock_purchase_tracker.calculate_prum.return_value = Decimal("2100.0")

        executor = DCAExecutor(mock_binance_client, dca_config)
        executor.tracker = mock_purchase_tracker

        # When
        should_execute, reason = executor.should_execute_purchase()

        # Then: Should buy (price <= PRUM with 3% buffer)
        assert should_execute is True

    def test_should_buy_when_no_existing_position(
        self, mocker, mock_binance_client, mock_purchase_tracker, dca_config
    ):
        """Should BUY for first purchase (no PRUM yet)."""
        # Patch PurchaseTracker to prevent DB connection
        mocker.patch("dca.dca_executor.PurchaseTracker")

        # Given: No PRUM (first purchase)
        mock_binance_client.get_symbol_price.return_value = Decimal("3000.0")
        mock_binance_client.get_klines.return_value = [
            create_kline(open_price=2900, close_price=3000),
            create_kline(open_price=3000, close_price=3050),
            create_kline(open_price=3050, close_price=3100),
        ]
        mock_purchase_tracker.calculate_prum.return_value = None  # No PRUM

        executor = DCAExecutor(mock_binance_client, dca_config)
        executor.tracker = mock_purchase_tracker

        # When
        should_execute, reason = executor.should_execute_purchase()

        # Then: Should buy (first purchase)
        assert should_execute is True
        assert "first purchase" in reason.lower() or "no existing position" in reason.lower()
