"""
Tests for DCA decision logic.

Tests the core buy/skip decision algorithm in isolation,
focusing on momentum analysis and PRUM comparison.
"""

from decimal import Decimal

import pytest

from dca.dca_executor import DCAExecutor
from tests.conftest import create_kline


@pytest.fixture
def mock_dca_config(mocker):
    """Create a mock DCA config for testing."""
    config = mocker.Mock()
    config.dca = mocker.Mock(
        symbol="ETHUSDC",
        base_asset="ETH",
        base_prum=None,
        base_quantity=0.0,
        prum_buffer=0.03,
        momentum_periods=2,
        kline_interval="1w",
    )
    return config


class TestDCADecisionLogic:
    """Tests for DCA buy/skip decision logic."""

    def test_should_skip_when_bullish_and_price_above_prum(
        self, mocker, mock_dca_config
    ):
        """
        Should skip purchase when all periods are bullish and price exceeds PRUM.

        Given: 2 consecutive positive periods AND current price above PRUM + buffer
        When: Evaluating whether to execute purchase
        Then: Returns False with skip reason
        """
        # Given
        mocker.patch("dca.dca_executor.PurchaseTracker")

        mock_client = mocker.Mock()
        mock_client.get_symbol_price.return_value = Decimal("3100.0")
        mock_client.get_klines.return_value = [
            create_kline(open_price=2900, close_price=3000),  # Positive
            create_kline(open_price=3000, close_price=3050),  # Positive
            create_kline(open_price=3050, close_price=3100),  # Current
        ]

        executor = DCAExecutor(mock_client, mock_dca_config)
        executor.tracker = mocker.Mock()
        executor.tracker.calculate_prum.return_value = Decimal("2000.0")

        # When
        should_execute, reason = executor.should_execute_purchase()

        # Then
        assert should_execute is False
        assert "skip" in reason.lower()

    def test_should_buy_when_one_negative_period(self, mocker, mock_dca_config):
        """
        Should execute purchase when at least one period is negative.

        Given: Mixed momentum with 1 negative and 1 positive period
        When: Evaluating whether to execute purchase
        Then: Returns True (non-bullish momentum triggers buy)
        """
        # Given
        mocker.patch("dca.dca_executor.PurchaseTracker")

        mock_client = mocker.Mock()
        mock_client.get_symbol_price.return_value = Decimal("3100.0")
        mock_client.get_klines.return_value = [
            create_kline(open_price=3200, close_price=3000),  # Negative
            create_kline(open_price=3000, close_price=3050),  # Positive
            create_kline(open_price=3050, close_price=3100),  # Current
        ]

        executor = DCAExecutor(mock_client, mock_dca_config)
        executor.tracker = mocker.Mock()
        executor.tracker.calculate_prum.return_value = Decimal("2000.0")

        # When
        should_execute, reason = executor.should_execute_purchase()

        # Then
        assert should_execute is True

    def test_should_buy_when_no_prum_first_purchase(self, mocker, mock_dca_config):
        """
        Should execute purchase when no existing position exists.

        Given: No previous purchases (PRUM is None)
        When: Evaluating whether to execute purchase
        Then: Returns True with reason indicating first purchase
        """
        # Given
        mocker.patch("dca.dca_executor.PurchaseTracker")

        mock_client = mocker.Mock()
        mock_client.get_symbol_price.return_value = Decimal("3000.0")
        mock_client.get_klines.return_value = [
            create_kline(open_price=2900, close_price=3000),
            create_kline(open_price=3000, close_price=3050),
            create_kline(open_price=3050, close_price=3100),
        ]

        executor = DCAExecutor(mock_client, mock_dca_config)
        executor.tracker = mocker.Mock()
        executor.tracker.calculate_prum.return_value = None

        # When
        should_execute, reason = executor.should_execute_purchase()

        # Then
        assert should_execute is True
        assert (
            "first purchase" in reason.lower()
            or "no existing position" in reason.lower()
        )
