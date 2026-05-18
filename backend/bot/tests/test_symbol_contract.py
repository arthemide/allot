"""
Non-regression tests for the symbol/asset_symbol contract.

The DCA bot uses TWO distinct identifiers that must never be confused:

* ``dca_config.symbol`` is the Binance **trading pair** (e.g. ``ETHUSDC``).
  It is passed to every Binance API call (price, klines, market orders).
* ``dca_config.asset_symbol`` is the **DB asset identifier** (e.g. ``ETH-USD``).
  It must match the symbol used by the fund app so transactions attach to the
  existing asset instead of creating a duplicate.

These tests pin the contract so a future refactor of the bot's config variables
fails loudly instead of silently mixing the two values.
"""

from decimal import Decimal

import pytest
import requests

from dca.dca_executor import DCAExecutor


@pytest.fixture
def dca_config(mocker):
    """Config where `symbol` (Binance pair) and `asset_symbol` (DB id) differ."""
    config = mocker.Mock()
    config.dca = mocker.Mock(
        symbol="ETHUSDC",  # Binance trading pair
        base_asset="ETH",
        quote_asset="USDC",
        asset_symbol="ETH-USD",  # DB identifier (must differ from `symbol`)
        asset_currency="USD",
        amount_usdc=30.0,
        base_prum=None,
        base_quantity=0.0,
        prum_buffer=0.03,
        momentum_periods=2,
        kline_interval="1w",
    )
    return config


class TestSymbolIsBinancePair:
    """`dca_config.symbol` must be the value used for every Binance API call."""

    def test_purchase_tracker_is_built_with_asset_symbol_not_binance_pair(
        self, mocker, mock_binance_client, dca_config
    ):
        """
        Given: a config where `symbol` ("ETHUSDC") != `asset_symbol` ("ETH-USD")
        When:  DCAExecutor is instantiated
        Then:  PurchaseTracker receives `asset_symbol`, NOT `symbol`
        """
        # Given
        tracker_cls = mocker.patch("dca.dca_executor.PurchaseTracker")

        # When
        DCAExecutor(mock_binance_client, dca_config)

        # Then
        kwargs = tracker_cls.call_args.kwargs
        assert kwargs["symbol"] == "ETH-USD", (
            "PurchaseTracker must be built with `asset_symbol` (DB id), "
            "not `symbol` (Binance trading pair). Got: " + repr(kwargs["symbol"])
        )
        assert kwargs["symbol"] != dca_config.dca.symbol, (
            "Regression: PurchaseTracker is using the Binance trading pair as "
            "asset id — this creates duplicate stocks rows."
        )

    def test_get_symbol_price_is_called_with_binance_pair(
        self, mocker, mock_binance_client, mock_purchase_tracker, dca_config
    ):
        """
        Given: a config where `symbol` is the Binance pair
        When:  should_execute_purchase queries the current price
        Then:  Binance receives `symbol` (the pair), not `asset_symbol`
        """
        # Given
        mocker.patch("dca.dca_executor.PurchaseTracker")
        mock_binance_client.get_symbol_price.return_value = Decimal("3000")
        mock_binance_client.get_klines.return_value = []
        mock_purchase_tracker.calculate_prum.return_value = None

        executor = DCAExecutor(mock_binance_client, dca_config)
        executor.tracker = mock_purchase_tracker

        # When
        executor.should_execute_purchase()

        # Then
        mock_binance_client.get_symbol_price.assert_called_with("ETHUSDC")

    def test_get_klines_is_called_with_binance_pair(
        self, mocker, mock_binance_client, mock_purchase_tracker, dca_config
    ):
        """
        Given: a config where `symbol` is the Binance pair
        When:  should_execute_purchase fetches klines
        Then:  Binance receives `symbol` (the pair), not `asset_symbol`
        """
        # Given
        mocker.patch("dca.dca_executor.PurchaseTracker")
        mock_binance_client.get_symbol_price.return_value = Decimal("3000")
        mock_binance_client.get_klines.return_value = []
        mock_purchase_tracker.calculate_prum.return_value = None

        executor = DCAExecutor(mock_binance_client, dca_config)
        executor.tracker = mock_purchase_tracker

        # When
        executor.should_execute_purchase()

        # Then
        call_args = mock_binance_client.get_klines.call_args
        # `get_klines(symbol, interval=..., limit=...)` — first positional arg
        assert call_args.args[0] == "ETHUSDC", (
            "get_klines must be called with the Binance trading pair "
            "(`symbol`), not the DB asset id. Got: " + repr(call_args.args[0])
        )

    def test_create_market_order_is_called_with_binance_pair(
        self, mocker, mock_binance_client, mock_purchase_tracker, dca_config
    ):
        """
        Given: a config where `symbol` is the Binance pair
        When:  execute_dca_purchase places a market order
        Then:  Binance receives `symbol` (the pair) as `symbol` kwarg
        """
        # Given
        mocker.patch("dca.dca_executor.PurchaseTracker")
        mocker.patch("dca.dca_executor.get_notifier")

        executor = DCAExecutor(mock_binance_client, dca_config)
        executor.tracker = mock_purchase_tracker
        mocker.patch.object(
            executor, "should_execute_purchase", return_value=(True, "ok")
        )
        mocker.patch.object(executor, "check_and_ensure_balance", return_value=True)
        mock_binance_client.get_symbol_price.return_value = Decimal("3000")

        order = mocker.Mock(
            order_id=1,
            status="FILLED",
            executed_qty=Decimal("0.01"),
            fills=[
                mocker.Mock(
                    qty=Decimal("0.01"),
                    price=Decimal("3000"),
                    commission=Decimal("0"),
                )
            ],
        )
        mock_binance_client.create_market_order.return_value = order

        # When
        executor.execute_dca_purchase()

        # Then
        kwargs = mock_binance_client.create_market_order.call_args.kwargs
        assert kwargs["symbol"] == "ETHUSDC", (
            "create_market_order must receive the Binance trading pair "
            "(`symbol`), not the DB asset id. Got: " + repr(kwargs["symbol"])
        )


class TestAssetSymbolIsDbIdentifier:
    """`dca_config.asset_symbol` must be the value tracked in DB."""

    def test_tracker_records_purchase_against_asset_symbol(
        self, mocker, mock_binance_client, mock_purchase_tracker, dca_config
    ):
        """
        Given: a config where `asset_symbol` differs from `symbol`
        When:  a purchase is recorded
        Then:  the tracker — built on `asset_symbol` — receives the purchase
        """
        # Given
        tracker_cls = mocker.patch(
            "dca.dca_executor.PurchaseTracker", return_value=mock_purchase_tracker
        )
        mocker.patch("dca.dca_executor.get_notifier")

        executor = DCAExecutor(mock_binance_client, dca_config)
        mocker.patch.object(
            executor, "should_execute_purchase", return_value=(True, "ok")
        )
        mocker.patch.object(executor, "check_and_ensure_balance", return_value=True)
        mock_binance_client.get_symbol_price.return_value = Decimal("3000")

        order = mocker.Mock(
            order_id=42,
            status="FILLED",
            executed_qty=Decimal("0.01"),
            fills=[
                mocker.Mock(
                    qty=Decimal("0.01"),
                    price=Decimal("3000"),
                    commission=Decimal("0"),
                )
            ],
        )
        mock_binance_client.create_market_order.return_value = order

        # When
        executor.execute_dca_purchase()

        # Then
        assert tracker_cls.call_args.kwargs["symbol"] == "ETH-USD"
        mock_purchase_tracker.add_purchase.assert_called_once()

    @pytest.mark.integration
    def test_default_symbol_is_a_valid_binance_pair(self):
        """
        Live check: the default `symbol` value is accepted by Binance's klines
        endpoint. Guards against a refactor that swaps `symbol` and
        `asset_symbol` (e.g. setting it to "ETH-USD"), which would still pass
        unit tests but break in production.

        Hits the public `/api/v3/klines` endpoint — no auth required.
        Skipped if the network is unreachable.
        """
        from dca.config import DCAConfig

        symbol = DCAConfig(amount_usdc=1000).symbol

        try:
            response = requests.get(
                "https://api.binance.com/api/v3/klines",
                params={"symbol": symbol, "interval": "1d", "limit": 1},
                timeout=5,
            )
        except requests.exceptions.RequestException as exc:
            pytest.skip(f"Binance unreachable: {exc}")

        assert response.status_code == 200, (
            f"Binance rejected DCAConfig().symbol={symbol!r} — likely a "
            f"regression where the DB asset id was passed as Binance pair. "
            f"Response: {response.text}"
        )
        assert response.json(), "Binance returned no klines for the symbol"

    def test_currency_is_propagated_to_tracker(
        self, mocker, mock_binance_client, dca_config
    ):
        """
        Given: a config with an explicit `asset_currency`
        When:  DCAExecutor is instantiated
        Then:  PurchaseTracker receives the same currency, so the DB asset row
               carries the right display currency for the front.
        """
        # Given
        dca_config.dca.asset_currency = "EUR"
        tracker_cls = mocker.patch("dca.dca_executor.PurchaseTracker")

        # When
        DCAExecutor(mock_binance_client, dca_config)

        # Then
        assert tracker_cls.call_args.kwargs["currency"] == "EUR"
