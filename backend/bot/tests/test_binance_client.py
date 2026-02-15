"""
Tests for BinanceClient - API communication, signature, and response parsing.
Tests all public methods with mocked HTTP session.
"""

from decimal import Decimal

import pytest
import requests

from dca.binance_client import BinanceAPIError, BinanceClient
from dca.config import BinanceConfig


@pytest.fixture
def client(mocker):
    """Create a BinanceClient with mocked requests.Session."""
    mocker.patch("dca.binance_client.requests.Session")
    config = BinanceConfig(api_key="test_key", api_secret="test_secret")
    return BinanceClient(config)


class TestBinanceClientInit:
    """Tests for BinanceClient initialization."""

    def test_should_initialize_with_api_keys(self, client):
        """
        Should store API keys and create HTTP session.

        Given: BinanceConfig with api_key and api_secret
        When: Creating BinanceClient
        Then: Keys stored and session headers set
        """
        assert client.api_key == "test_key"
        assert client.api_secret == "test_secret"


class TestGenerateSignature:
    """Tests for HMAC SHA256 signature generation."""

    def test_should_generate_64_char_hex_signature(self, client):
        """
        Should generate a valid 64-character hexadecimal HMAC SHA256 signature.

        Given: Request parameters dict
        When: Generating signature
        Then: Returns 64-char hex string
        """
        # Given
        params = {"symbol": "ETHUSDC", "timestamp": 1234567890}

        # When
        signature = client._generate_signature(params)

        # Then
        assert isinstance(signature, str)
        assert len(signature) == 64


class TestRequest:
    """Tests for _request method - core HTTP communication."""

    def test_should_return_json_on_200(self, client):
        """
        Should return parsed JSON when API returns 200.

        Given: API returns 200 with JSON body
        When: Making a request
        Then: Returns the parsed JSON dict
        """
        # Given
        mock_response = client.session.request.return_value
        mock_response.status_code = 200
        mock_response.json.return_value = {"key": "value"}

        # When
        result = client._request("GET", "/api/v3/test")

        # Then
        assert result == {"key": "value"}

    def test_should_raise_binance_api_error_on_non_200(self, client):
        """
        Should raise BinanceAPIError when API returns error status.

        Given: API returns 400 with error message
        When: Making a request
        Then: BinanceAPIError raised with message and code
        """
        # Given
        mock_response = client.session.request.return_value
        mock_response.status_code = 400
        mock_response.json.return_value = {"code": -1100, "msg": "Bad request"}

        # When / Then
        with pytest.raises(BinanceAPIError, match="Bad request"):
            client._request("GET", "/api/v3/test")

    def test_should_raise_on_network_error(self, client):
        """
        Should wrap network errors in BinanceAPIError.

        Given: Network connection fails
        When: Making a request
        Then: BinanceAPIError raised with network error info
        """
        # Given
        client.session.request.side_effect = (
            requests.exceptions.ConnectionError("timeout")
        )

        # When / Then
        with pytest.raises(BinanceAPIError, match="Network error"):
            client._request("GET", "/api/v3/test")

    def test_should_add_timestamp_and_signature_when_signed(self, client, mocker):
        """
        Should add timestamp and HMAC signature for signed requests.

        Given: signed=True
        When: Making a signed request
        Then: params contain timestamp and signature
        """
        # Given
        mock_response = client.session.request.return_value
        mock_response.status_code = 200
        mock_response.json.return_value = {}
        mocker.patch("dca.binance_client.time.time", return_value=1234567.890)

        # When
        client._request("GET", "/api/v3/account", signed=True, params={"symbol": "ETH"})

        # Then
        call_kwargs = client.session.request.call_args
        params = call_kwargs[1]["params"]
        assert "timestamp" in params
        assert "signature" in params


class TestGetAssetBalance:
    """Tests for get_asset_balance method."""

    def test_should_return_balance_when_asset_found(self, client, mocker):
        """
        Should return correct free, locked, and total when asset exists.

        Given: Account has USDC with free=100 and locked=10
        When: Getting USDC balance
        Then: Returns AssetBalance with correct amounts
        """
        # Given
        mocker.patch.object(
            client,
            "get_account_info",
            return_value={
                "balances": [
                    {"asset": "USDC", "free": "100.0", "locked": "10.0"},
                    {"asset": "ETH", "free": "0.5", "locked": "0.0"},
                ]
            },
        )

        # When
        balance = client.get_asset_balance("USDC")

        # Then
        assert balance.free == Decimal("100.0")
        assert balance.locked == Decimal("10.0")
        assert balance.total == Decimal("110.0")

    def test_should_return_zero_when_asset_not_found(self, client, mocker):
        """
        Should return zero balance when asset is not in account.

        Given: Account has no USDC
        When: Getting USDC balance
        Then: Returns AssetBalance with all zeros
        """
        # Given
        mocker.patch.object(
            client,
            "get_account_info",
            return_value={
                "balances": [{"asset": "BTC", "free": "1.0", "locked": "0.0"}]
            },
        )

        # When
        balance = client.get_asset_balance("USDC")

        # Then
        assert balance.free == Decimal("0")
        assert balance.total == Decimal("0")


class TestGetSymbolInfo:
    """Tests for get_symbol_info method."""

    def test_should_return_symbol_info(self, client, mocker):
        """
        Should return first symbol entry from exchange info.

        Given: Exchange info contains ETHUSDC
        When: Getting symbol info
        Then: Returns the symbol dict
        """
        # Given
        mocker.patch.object(
            client,
            "_request",
            return_value={"symbols": [{"symbol": "ETHUSDC", "status": "TRADING"}]},
        )

        # When
        result = client.get_symbol_info("ETHUSDC")

        # Then
        assert result["symbol"] == "ETHUSDC"

    def test_should_raise_when_symbol_not_found(self, client, mocker):
        """
        Should raise BinanceAPIError when symbol does not exist.

        Given: Exchange info returns empty symbols list
        When: Getting info for invalid symbol
        Then: BinanceAPIError raised
        """
        # Given
        mocker.patch.object(client, "_request", return_value={"symbols": []})

        # When / Then
        with pytest.raises(BinanceAPIError, match="not found"):
            client.get_symbol_info("INVALID")


class TestGetSymbolPrice:
    """Tests for get_symbol_price method."""

    def test_should_return_decimal_price(self, client, mocker):
        """
        Should return current price as Decimal.

        Given: Ticker API returns price "3000.50"
        When: Getting symbol price
        Then: Returns Decimal("3000.50")
        """
        # Given
        mocker.patch.object(client, "_request", return_value={"price": "3000.50"})

        # When
        price = client.get_symbol_price("ETHUSDC")

        # Then
        assert price == Decimal("3000.50")


class TestCreateMarketOrder:
    """Tests for create_market_order method."""

    def _make_order_response(self):
        """Helper to create a standard order response."""
        return {
            "symbol": "ETHUSDC",
            "orderId": 12345,
            "clientOrderId": "abc123",
            "transactTime": 1234567890,
            "price": "0.0",
            "origQty": "0.01",
            "executedQty": "0.01",
            "cummulativeQuoteQty": "30.0",
            "status": "FILLED",
            "type": "MARKET",
            "side": "BUY",
            "fills": [
                {
                    "price": "3000.0",
                    "qty": "0.01",
                    "commission": "0.00001",
                    "commissionAsset": "ETH",
                }
            ],
        }

    def test_should_create_order_with_quote_qty(self, client, mocker):
        """
        Should create market order using quote currency amount.

        Given: Valid order response from API
        When: Creating market BUY order with quote_order_qty
        Then: Returns MarketOrder with correct fields
        """
        # Given
        mocker.patch.object(client, "_request", return_value=self._make_order_response())

        # When
        order = client.create_market_order("ETHUSDC", "BUY", quote_order_qty="30")

        # Then
        assert order.order_id == 12345
        assert order.status == "FILLED"
        assert order.executed_qty == Decimal("0.01")
        assert len(order.fills) == 1

    def test_should_create_order_with_quantity(self, client, mocker):
        """
        Should create market order using base currency quantity.

        Given: Valid order response from API
        When: Creating market BUY order with quantity
        Then: Returns MarketOrder with correct fields
        """
        # Given
        mocker.patch.object(client, "_request", return_value=self._make_order_response())

        # When
        order = client.create_market_order("ETHUSDC", "BUY", quantity="0.01")

        # Then
        assert order.order_id == 12345

    def test_should_raise_when_no_qty_specified(self, client):
        """
        Should raise ValueError when neither quote_order_qty nor quantity provided.

        Given: No quantity parameters
        When: Creating market order
        Then: ValueError raised
        """
        # When / Then
        with pytest.raises(ValueError, match="quote_order_qty"):
            client.create_market_order("ETHUSDC", "BUY")


class TestGetSimpleEarnFlexiblePosition:
    """Tests for get_simple_earn_flexible_position method."""

    def test_should_parse_positions_from_response(self, client, mocker):
        """
        Should parse flexible positions from API rows.

        Given: API returns one USDC position
        When: Getting flexible positions
        Then: Returns list with one FlexiblePosition
        """
        # Given
        mocker.patch.object(
            client,
            "_request",
            return_value={
                "rows": [
                    {
                        "asset": "USDC",
                        "totalAmount": "500.0",
                        "productId": "USDC001",
                    }
                ]
            },
        )

        # When
        positions = client.get_simple_earn_flexible_position(asset="USDC")

        # Then
        assert len(positions) == 1
        assert positions[0].asset == "USDC"
        assert positions[0].total_amount == Decimal("500.0")

    def test_should_return_empty_list_when_no_positions(self, client, mocker):
        """
        Should return empty list when no flexible positions exist.

        Given: API returns empty rows
        When: Getting flexible positions
        Then: Returns empty list
        """
        # Given
        mocker.patch.object(client, "_request", return_value={"rows": []})

        # When
        positions = client.get_simple_earn_flexible_position()

        # Then
        assert positions == []


class TestRedeemFlexibleProduct:
    """Tests for redeem_flexible_product method."""

    def test_should_return_redeem_response(self, client, mocker):
        """
        Should return RedeemResponse on successful redemption.

        Given: API returns success with redeemId
        When: Redeeming flexible product
        Then: Returns RedeemResponse with success=True
        """
        # Given
        mocker.patch.object(
            client,
            "_request",
            return_value={"redeemId": 42, "success": True},
        )

        # When
        result = client.redeem_flexible_product("USDC001", "100.0")

        # Then
        assert result.success is True
        assert result.redeem_id == 42


class TestGetFlexibleProductPositionByAsset:
    """Tests for get_flexible_product_position_by_asset method."""

    def test_should_return_position_when_found_with_balance(self, client, mocker):
        """
        Should return position when asset exists with positive balance.

        Given: Flexible position with 500 USDC
        When: Getting position for USDC
        Then: Returns the FlexiblePosition
        """
        # Given
        mock_position = mocker.Mock(
            asset="USDC", total_amount=Decimal("500.0"), product_id="USDC001"
        )
        mocker.patch.object(
            client,
            "get_simple_earn_flexible_position",
            return_value=[mock_position],
        )

        # When
        position = client.get_flexible_product_position_by_asset("USDC")

        # Then
        assert position is not None
        assert position.asset == "USDC"

    def test_should_return_none_when_no_positions(self, client, mocker):
        """
        Should return None when no positions exist for asset.

        Given: No flexible positions
        When: Getting position for USDC
        Then: Returns None
        """
        # Given
        mocker.patch.object(
            client, "get_simple_earn_flexible_position", return_value=[]
        )

        # When
        position = client.get_flexible_product_position_by_asset("USDC")

        # Then
        assert position is None

    def test_should_return_none_when_balance_is_zero(self, client, mocker):
        """
        Should return None when position exists but balance is zero.

        Given: Flexible position with 0 USDC
        When: Getting position for USDC
        Then: Returns None
        """
        # Given
        mock_position = mocker.Mock(
            asset="USDC", total_amount=Decimal("0"), product_id="USDC001"
        )
        mocker.patch.object(
            client,
            "get_simple_earn_flexible_position",
            return_value=[mock_position],
        )

        # When
        position = client.get_flexible_product_position_by_asset("USDC")

        # Then
        assert position is None


class TestGetKlines:
    """Tests for get_klines method."""

    def test_should_parse_kline_arrays(self, client, mocker):
        """
        Should parse raw kline arrays into Kline objects.

        Given: API returns 2 kline arrays
        When: Getting klines
        Then: Returns list of Kline with correct OHLCV values
        """
        # Given
        mocker.patch.object(
            client,
            "_request",
            return_value=[
                [1000, "3000.0", "3100.0", "2900.0", "3050.0", "100.0", 1999],
                [2000, "3050.0", "3200.0", "3000.0", "3150.0", "120.0", 2999],
            ],
        )

        # When
        klines = client.get_klines("ETHUSDC", "1w", limit=2)

        # Then
        assert len(klines) == 2
        assert klines[0].open == Decimal("3000.0")
        assert klines[0].close == Decimal("3050.0")
        assert klines[1].open == Decimal("3050.0")


class TestGetAllOrders:
    """Tests for get_all_orders method."""

    def test_should_return_order_list(self, client, mocker):
        """
        Should return list of order dicts from API.

        Given: API returns 2 orders
        When: Getting all orders
        Then: Returns list of 2 order dicts
        """
        # Given
        mocker.patch.object(
            client,
            "_request",
            return_value=[
                {"orderId": 1, "symbol": "ETHUSDC"},
                {"orderId": 2, "symbol": "ETHUSDC"},
            ],
        )

        # When
        orders = client.get_all_orders("ETHUSDC")

        # Then
        assert len(orders) == 2
