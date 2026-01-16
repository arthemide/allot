"""
Simple tests for DCA decision logic - the most critical part.
Keep it simple: test the buy/skip decision without complex setup.
"""

from decimal import Decimal

from dca.dca_executor import DCAExecutor
from tests.conftest import create_kline


class TestDCADecisionLogic:
    """Test when DCA should buy vs skip."""

    def test_should_skip_when_bullish_and_price_above_prum(self, mocker):
        """Should SKIP if both periods positive AND price > PRUM."""
        # Patch PurchaseTracker to prevent DB connection
        mocker.patch("dca.dca_executor.PurchaseTracker")

        # Setup mock config
        mock_config = mocker.Mock()
        mock_config.dca = mocker.Mock(
            symbol="ETHUSDC", base_asset="ETH", base_prum=None, base_quantity=0.0
        )

        # Setup mock client
        mock_client = mocker.Mock()
        mock_client.get_symbol_price.return_value = Decimal("3100.0")
        mock_client.get_klines.return_value = [
            create_kline(open_price=2900, close_price=3000),  # Positive
            create_kline(open_price=3000, close_price=3050),  # Positive
            create_kline(open_price=3050, close_price=3100),  # Current
        ]

        executor = DCAExecutor(mock_client, mock_config)
        executor.tracker = mocker.Mock()
        executor.tracker.calculate_prum.return_value = Decimal("2000.0")

        # When
        should_execute, reason = executor.should_execute_purchase()

        # Then: Should skip (bullish + price above PRUM)
        assert should_execute is False
        assert "skip" in reason.lower()

    def test_should_buy_when_one_negative_period(self, mocker):
        """Should BUY if at least one period is negative."""
        # Patch PurchaseTracker to prevent DB connection
        mocker.patch("dca.dca_executor.PurchaseTracker")

        # Setup mock config
        mock_config = mocker.Mock()
        mock_config.dca = mocker.Mock(
            symbol="ETHUSDC", base_asset="ETH", base_prum=None, base_quantity=0.0
        )

        # Setup mock client
        mock_client = mocker.Mock()
        mock_client.get_symbol_price.return_value = Decimal("3100.0")
        mock_client.get_klines.return_value = [
            create_kline(open_price=3200, close_price=3000),  # Negative
            create_kline(open_price=3000, close_price=3050),  # Positive
            create_kline(open_price=3050, close_price=3100),  # Current
        ]

        executor = DCAExecutor(mock_client, mock_config)
        executor.tracker = mocker.Mock()
        executor.tracker.calculate_prum.return_value = Decimal("2000.0")

        # When
        should_execute, reason = executor.should_execute_purchase()

        # Then: Should buy
        assert should_execute is True

    def test_should_buy_when_no_prum_first_purchase(self, mocker):
        """Should BUY for first purchase (no PRUM yet)."""
        # Patch PurchaseTracker to prevent DB connection
        mocker.patch("dca.dca_executor.PurchaseTracker")

        # Setup mock config
        mock_config = mocker.Mock()
        mock_config.dca = mocker.Mock(
            symbol="ETHUSDC", base_asset="ETH", base_prum=None, base_quantity=0.0
        )

        # Setup mock client
        mock_client = mocker.Mock()
        mock_client.get_symbol_price.return_value = Decimal("3000.0")
        mock_client.get_klines.return_value = [
            create_kline(open_price=2900, close_price=3000),
            create_kline(open_price=3000, close_price=3050),
            create_kline(open_price=3050, close_price=3100),
        ]

        executor = DCAExecutor(mock_client, mock_config)
        executor.tracker = mocker.Mock()
        executor.tracker.calculate_prum.return_value = None  # No PRUM

        # When
        should_execute, reason = executor.should_execute_purchase()

        # Then: Should buy (first purchase)
        assert should_execute is True
        assert (
            "first purchase" in reason.lower()
            or "no existing position" in reason.lower()
        )
