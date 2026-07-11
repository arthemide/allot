"""
Tests for DCAExecutor - decision logic, balance management, and purchase execution.

Tests the core buy/skip decision algorithm, balance checking with earn transfer,
full purchase execution flow, and the run() entry point.
"""

from decimal import Decimal

import pytest

from dca.binance_client import BinanceAPIError
from dca.dca_executor import DCAExecutor, create_dca_executor
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
        base_quantity=0.0,
        prum_buffer=0.03,
        momentum_periods=2,
        kline_interval="1w",
    )
    return config


class TestDCADecisionLogic:
    """Tests for DCA buy/skip decision logic."""

    def test_should_skip_when_two_positive_periods_and_price_above_prum(
        self, mocker, mock_binance_client, mock_purchase_tracker, dca_config
    ):
        """
        Should skip purchase when all periods are bullish and price exceeds PRUM.

        Given: 2 consecutive positive periods AND current price above PRUM + buffer
        When: Evaluating whether to execute purchase
        Then: Returns False with reason indicating bullish skip
        """
        # Given
        mocker.patch("dca.dca_executor.PurchaseTracker")
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

        # Then
        assert should_execute is False
        assert "skip" in reason.lower() or "bullish" in reason.lower()

    def test_should_buy_when_one_negative_period(
        self, mocker, mock_binance_client, mock_purchase_tracker, dca_config
    ):
        """
        Should execute purchase when at least one period is negative.

        Given: Mixed momentum with 1 negative and 1 positive period
        When: Evaluating whether to execute purchase
        Then: Returns True (non-bullish momentum triggers buy)
        """
        # Given
        mocker.patch("dca.dca_executor.PurchaseTracker")
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

        # Then
        assert should_execute is True

    def test_should_buy_when_price_below_prum(
        self, mocker, mock_binance_client, mock_purchase_tracker, dca_config
    ):
        """
        Should execute purchase when price is below PRUM threshold.

        Given: 2 positive periods but current price below PRUM + buffer
        When: Evaluating whether to execute purchase
        Then: Returns True (price advantage overrides bullish momentum)
        """
        # Given
        mocker.patch("dca.dca_executor.PurchaseTracker")
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

        # Then
        assert should_execute is True

    def test_should_buy_when_no_existing_position(
        self, mocker, mock_binance_client, mock_purchase_tracker, dca_config
    ):
        """
        Should execute purchase when no existing position exists.

        Given: No previous purchases (PRUM is None)
        When: Evaluating whether to execute purchase
        Then: Returns True with reason indicating first purchase
        """
        # Given
        mocker.patch("dca.dca_executor.PurchaseTracker")
        mock_binance_client.get_symbol_price.return_value = Decimal("3000.0")
        mock_binance_client.get_klines.return_value = [
            create_kline(open_price=2900, close_price=3000),
            create_kline(open_price=3000, close_price=3050),
            create_kline(open_price=3050, close_price=3100),
        ]
        mock_purchase_tracker.calculate_prum.return_value = None

        executor = DCAExecutor(mock_binance_client, dca_config)
        executor.tracker = mock_purchase_tracker

        # When
        should_execute, reason = executor.should_execute_purchase()

        # Then
        assert should_execute is True
        assert (
            "first purchase" in reason.lower()
            or "no existing position" in reason.lower()
        )


class TestShouldExecutePurchaseEdgeCases:
    """Tests for edge cases in should_execute_purchase."""

    def test_should_execute_when_insufficient_historical_data(
        self, mocker, mock_binance_client, dca_config
    ):
        """
        Should execute by default when not enough kline data available.

        Given: Only 2 klines returned (need 3 for momentum_periods=2)
        When: Evaluating purchase decision
        Then: Returns True with insufficient data reason
        """
        # Given
        mocker.patch("dca.dca_executor.PurchaseTracker")
        mock_binance_client.get_symbol_price.return_value = Decimal("3000.0")
        mock_binance_client.get_klines.return_value = [
            create_kline(open_price=2900, close_price=3000),
            create_kline(open_price=3000, close_price=3050),
        ]

        executor = DCAExecutor(mock_binance_client, dca_config)

        # When
        should_execute, reason = executor.should_execute_purchase()

        # Then
        assert should_execute is True
        assert "insufficient" in reason.lower()

    def test_should_execute_when_error_occurs(
        self, mocker, mock_binance_client, dca_config
    ):
        """
        Should execute by default when an error occurs during analysis.

        Given: get_symbol_price raises an exception
        When: Evaluating purchase decision
        Then: Returns True with error reason
        """
        # Given
        mocker.patch("dca.dca_executor.PurchaseTracker")
        mock_binance_client.get_symbol_price.side_effect = Exception("API down")

        executor = DCAExecutor(mock_binance_client, dca_config)

        # When
        should_execute, reason = executor.should_execute_purchase()

        # Then
        assert should_execute is True
        assert "error" in reason.lower()


class TestCheckAndEnsureBalance:
    """Tests for check_and_ensure_balance method."""

    def test_should_return_true_when_sufficient_balance(
        self, mocker, mock_binance_client, dca_config
    ):
        """
        Should return True when spot balance covers the required amount.

        Given: Free USDC balance is 50, required is 30
        When: Checking balance
        Then: Returns True without checking earn
        """
        # Given
        mocker.patch("dca.dca_executor.PurchaseTracker")
        mock_binance_client.get_asset_balance.return_value = mocker.Mock(
            free=Decimal("50.0")
        )

        executor = DCAExecutor(mock_binance_client, dca_config)

        # When
        result = executor.check_and_ensure_balance(Decimal("30.0"))

        # Then
        assert result is True
        mock_binance_client.get_flexible_product_position_by_asset.assert_not_called()

    def test_should_transfer_from_earn_when_insufficient_spot(
        self, mocker, mock_binance_client, dca_config
    ):
        """
        Should transfer from earn and return True when spot is insufficient.

        Given: Spot has 10 USDC, earn has 500 USDC, need 30
        When: Checking balance
        Then: Redeems from earn and returns True after recheck
        """
        # Given
        mocker.patch("dca.dca_executor.PurchaseTracker")
        mock_binance_client.get_asset_balance.side_effect = [
            mocker.Mock(free=Decimal("10.0")),  # First check: insufficient
            mocker.Mock(free=Decimal("30.0")),  # After transfer: sufficient
        ]
        mock_binance_client.get_flexible_product_position_by_asset.return_value = (
            mocker.Mock(
                asset="USDC",
                total_amount=Decimal("500.0"),
                product_id="USDC001",
            )
        )
        mock_binance_client.redeem_flexible_product.return_value = mocker.Mock(
            success=True
        )

        executor = DCAExecutor(mock_binance_client, dca_config)

        # When
        result = executor.check_and_ensure_balance(Decimal("30.0"))

        # Then
        assert result is True
        mock_binance_client.redeem_flexible_product.assert_called_once()

    def test_should_return_false_when_no_earn_position(
        self, mocker, mock_binance_client, dca_config
    ):
        """
        Should return False when spot is insufficient and no earn position exists.

        Given: Spot has 10 USDC, no earn position
        When: Checking balance
        Then: Returns False
        """
        # Given
        mocker.patch("dca.dca_executor.PurchaseTracker")
        mock_binance_client.get_asset_balance.return_value = mocker.Mock(
            free=Decimal("10.0")
        )
        mock_binance_client.get_flexible_product_position_by_asset.return_value = None

        executor = DCAExecutor(mock_binance_client, dca_config)

        # When
        result = executor.check_and_ensure_balance(Decimal("30.0"))

        # Then
        assert result is False

    def test_should_return_false_when_earn_amount_insufficient(
        self, mocker, mock_binance_client, dca_config
    ):
        """
        Should return False when earn balance doesn't cover the shortage.

        Given: Spot has 10, need 30, earn has only 5
        When: Checking balance
        Then: Returns False
        """
        # Given
        mocker.patch("dca.dca_executor.PurchaseTracker")
        mock_binance_client.get_asset_balance.return_value = mocker.Mock(
            free=Decimal("10.0")
        )
        mock_binance_client.get_flexible_product_position_by_asset.return_value = (
            mocker.Mock(
                asset="USDC",
                total_amount=Decimal("5.0"),
                product_id="USDC001",
            )
        )

        executor = DCAExecutor(mock_binance_client, dca_config)

        # When
        result = executor.check_and_ensure_balance(Decimal("30.0"))

        # Then
        assert result is False

    def test_should_return_false_when_still_insufficient_after_transfer(
        self, mocker, mock_binance_client, dca_config
    ):
        """
        Should return False when balance is still insufficient after earn transfer.

        Given: Transfer succeeds but balance still not enough
        When: Checking balance
        Then: Returns False
        """
        # Given
        mocker.patch("dca.dca_executor.PurchaseTracker")
        mock_binance_client.get_asset_balance.side_effect = [
            mocker.Mock(free=Decimal("10.0")),  # Before transfer
            mocker.Mock(free=Decimal("15.0")),  # After transfer (still not enough)
        ]
        mock_binance_client.get_flexible_product_position_by_asset.return_value = (
            mocker.Mock(
                asset="USDC",
                total_amount=Decimal("100.0"),
                product_id="USDC001",
            )
        )
        mock_binance_client.redeem_flexible_product.return_value = mocker.Mock(
            success=True
        )

        executor = DCAExecutor(mock_binance_client, dca_config)

        # When
        result = executor.check_and_ensure_balance(Decimal("30.0"))

        # Then
        assert result is False

    def test_should_return_false_on_earn_api_error(
        self, mocker, mock_binance_client, dca_config
    ):
        """
        Should return False when earn API call raises BinanceAPIError.

        Given: Spot insufficient and earn API raises error
        When: Checking balance
        Then: Returns False
        """
        # Given
        mocker.patch("dca.dca_executor.PurchaseTracker")
        mock_binance_client.get_asset_balance.return_value = mocker.Mock(
            free=Decimal("10.0")
        )
        mock_binance_client.get_flexible_product_position_by_asset.side_effect = (
            BinanceAPIError("Earn API down")
        )

        executor = DCAExecutor(mock_binance_client, dca_config)

        # When
        result = executor.check_and_ensure_balance(Decimal("30.0"))

        # Then
        assert result is False


class TestExecuteDCAPurchase:
    """Tests for execute_dca_purchase method."""

    def test_should_return_order_on_success(
        self, mocker, mock_binance_client, mock_purchase_tracker, dca_config
    ):
        """
        Should execute full purchase flow and return order result.

        Given: Decision is execute, balance sufficient, order fills
        When: Executing DCA purchase
        Then: Returns MarketOrder, records purchase, sends notification
        """
        # Given
        mocker.patch("dca.dca_executor.PurchaseTracker")
        mock_notifier = mocker.patch("dca.dca_executor.get_notifier")

        executor = DCAExecutor(mock_binance_client, dca_config)
        executor.tracker = mock_purchase_tracker

        mocker.patch.object(
            executor,
            "should_execute_purchase",
            return_value=(True, "Execute: conditions met"),
        )
        mocker.patch.object(executor, "check_and_ensure_balance", return_value=True)

        mock_binance_client.get_symbol_price.return_value = Decimal("3000.0")

        mock_order = mocker.Mock()
        mock_order.order_id = 12345
        mock_order.status = "FILLED"
        mock_order.executed_qty = Decimal("0.01")
        mock_order.fills = [
            mocker.Mock(
                qty=Decimal("0.01"),
                price=Decimal("3000.0"),
                commission=Decimal("0.00001"),
            )
        ]
        mock_binance_client.create_market_order.return_value = mock_order

        # When
        result = executor.execute_dca_purchase()

        # Then
        assert result is not None
        assert result.order_id == 12345
        mock_purchase_tracker.add_purchase.assert_called_once()
        mock_notifier.return_value.notify_purchase_success.assert_called_once()

    def test_should_apply_commissions_to_recorded_purchase(
        self, mocker, mock_binance_client, mock_purchase_tracker, dca_config
    ):
        """
        Should deduct base-asset fees from quantity and add quote-asset fees to cost.

        Given: An order with one fill paying commission in ETH and one in USDC
        When: Executing DCA purchase
        Then: Recorded quantity is net of the ETH commission and recorded cost
              includes the USDC commission
        """
        # Given
        mocker.patch("dca.dca_executor.PurchaseTracker")
        mocker.patch("dca.dca_executor.get_notifier")

        executor = DCAExecutor(mock_binance_client, dca_config)
        executor.tracker = mock_purchase_tracker

        mocker.patch.object(
            executor,
            "should_execute_purchase",
            return_value=(True, "Execute: conditions met"),
        )
        mocker.patch.object(executor, "check_and_ensure_balance", return_value=True)

        mock_binance_client.get_symbol_price.return_value = Decimal("3000.0")

        mock_order = mocker.Mock()
        mock_order.order_id = 12345
        mock_order.status = "FILLED"
        mock_order.executed_qty = Decimal("0.01")
        mock_order.fills = [
            mocker.Mock(
                qty=Decimal("0.005"),
                price=Decimal("3000.0"),
                commission=Decimal("0.000005"),
                commission_asset="ETH",
            ),
            mocker.Mock(
                qty=Decimal("0.005"),
                price=Decimal("3000.0"),
                commission=Decimal("0.015"),
                commission_asset="USDC",
            ),
        ]
        mock_binance_client.create_market_order.return_value = mock_order

        # When
        executor.execute_dca_purchase()

        # Then
        call_kwargs = mock_purchase_tracker.add_purchase.call_args.kwargs
        assert call_kwargs["quantity"] == Decimal("0.01") - Decimal("0.000005")
        assert call_kwargs["total_cost"] == Decimal("30.0") + Decimal("0.015")

    def test_should_return_none_when_purchase_skipped(
        self, mocker, mock_binance_client, mock_purchase_tracker, dca_config
    ):
        """
        Should return None and send skip notification when decision is skip.

        Given: Decision logic says skip
        When: Executing DCA purchase
        Then: Returns None, sends skip notification, no order created
        """
        # Given
        mocker.patch("dca.dca_executor.PurchaseTracker")
        mock_notifier = mocker.patch("dca.dca_executor.get_notifier")

        executor = DCAExecutor(mock_binance_client, dca_config)
        executor.tracker = mock_purchase_tracker

        mocker.patch.object(
            executor,
            "should_execute_purchase",
            return_value=(False, "Bullish momentum"),
        )

        # When
        result = executor.execute_dca_purchase()

        # Then
        assert result is None
        mock_notifier.return_value.notify_purchase_skipped.assert_called_once()
        mock_binance_client.create_market_order.assert_not_called()

    def test_should_return_none_when_insufficient_balance(
        self, mocker, mock_binance_client, mock_purchase_tracker, dca_config
    ):
        """
        Should return None and send error notification when balance insufficient.

        Given: Decision is execute but balance check fails
        When: Executing DCA purchase
        Then: Returns None, sends error notification
        """
        # Given
        mocker.patch("dca.dca_executor.PurchaseTracker")
        mock_notifier = mocker.patch("dca.dca_executor.get_notifier")

        executor = DCAExecutor(mock_binance_client, dca_config)
        executor.tracker = mock_purchase_tracker

        mocker.patch.object(
            executor,
            "should_execute_purchase",
            return_value=(True, "Execute"),
        )
        mocker.patch.object(executor, "check_and_ensure_balance", return_value=False)

        # When
        result = executor.execute_dca_purchase()

        # Then
        assert result is None
        mock_notifier.return_value.notify_error.assert_called_once()
        mock_binance_client.create_market_order.assert_not_called()

    def test_should_return_none_on_api_error(
        self, mocker, mock_binance_client, mock_purchase_tracker, dca_config
    ):
        """
        Should catch BinanceAPIError and return None.

        Given: Market order raises BinanceAPIError
        When: Executing DCA purchase
        Then: Returns None, sends error notification
        """
        # Given
        mocker.patch("dca.dca_executor.PurchaseTracker")
        mock_notifier = mocker.patch("dca.dca_executor.get_notifier")

        executor = DCAExecutor(mock_binance_client, dca_config)
        executor.tracker = mock_purchase_tracker

        mocker.patch.object(
            executor,
            "should_execute_purchase",
            return_value=(True, "Execute"),
        )
        mocker.patch.object(executor, "check_and_ensure_balance", return_value=True)
        mock_binance_client.get_symbol_price.return_value = Decimal("3000.0")
        mock_binance_client.create_market_order.side_effect = BinanceAPIError(
            "Order failed"
        )

        # When
        result = executor.execute_dca_purchase()

        # Then
        assert result is None
        mock_notifier.return_value.notify_error.assert_called_once()


class TestRun:
    """Tests for run() entry point method."""

    def test_should_return_true_on_success(
        self, mocker, mock_binance_client, dca_config
    ):
        """
        Should return True when execute_dca_purchase returns an order.

        Given: execute_dca_purchase returns a result
        When: Calling run()
        Then: Returns True
        """
        # Given
        mocker.patch("dca.dca_executor.PurchaseTracker")

        executor = DCAExecutor(mock_binance_client, dca_config)

        mock_order = mocker.Mock()
        mocker.patch.object(executor, "execute_dca_purchase", return_value=mock_order)

        # When
        result = executor.run()

        # Then
        assert result is True

    def test_should_return_false_when_purchase_skipped_or_failed(
        self, mocker, mock_binance_client, dca_config
    ):
        """
        Should return False when execute_dca_purchase returns None.

        Given: execute_dca_purchase returns None
        When: Calling run()
        Then: Returns False
        """
        # Given
        mocker.patch("dca.dca_executor.PurchaseTracker")

        executor = DCAExecutor(mock_binance_client, dca_config)

        mocker.patch.object(executor, "execute_dca_purchase", return_value=None)

        # When
        result = executor.run()

        # Then
        assert result is False

    def test_should_return_false_on_exception(
        self, mocker, mock_binance_client, dca_config
    ):
        """
        Should return False when execute_dca_purchase raises an exception.

        Given: execute_dca_purchase raises Exception
        When: Calling run()
        Then: Returns False
        """
        # Given
        mocker.patch("dca.dca_executor.PurchaseTracker")

        executor = DCAExecutor(mock_binance_client, dca_config)

        mocker.patch.object(
            executor,
            "execute_dca_purchase",
            side_effect=Exception("Unexpected"),
        )

        # When
        result = executor.run()

        # Then
        assert result is False


class TestCreateDCAExecutor:
    """Tests for create_dca_executor factory function."""

    def test_should_create_executor_with_binance_client(self, mocker, dca_config):
        """
        Should create DCAExecutor with a BinanceClient from config.

        Given: Valid config with binance credentials
        When: Calling create_dca_executor
        Then: Returns DCAExecutor instance
        """
        # Given
        mocker.patch("dca.dca_executor.PurchaseTracker")
        mock_binance_class = mocker.patch("dca.dca_executor.BinanceClient")

        # When
        executor = create_dca_executor(dca_config)

        # Then
        assert isinstance(executor, DCAExecutor)
        mock_binance_class.assert_called_once_with(dca_config.binance)
