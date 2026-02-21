"""
Tests for FastAPI endpoints using TestClient.

Tests HTTP layer with mocked services — verifies status codes,
response schemas, and correct service method calls.
"""

from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from src.main import app
from src.models.pydantic.schema import FundSchema, StockSchema, TransactionSchema


@pytest.fixture
def client():
    """Create a FastAPI TestClient."""
    return TestClient(app)


# ── Shared test data ──────────────────────────────────────────────


def make_fund_schema(
    fund_id="1",
    name="Test Fund",
    stocks=None,
):
    """Helper to create a FundSchema for test assertions."""
    return FundSchema(
        id=fund_id,
        fund_name=name,
        stocks=stocks or [],
        created_at=datetime(2026, 1, 1),
        updated_at=datetime(2026, 1, 1),
        total_cost=0.0,
        total_market_value=0.0,
        total_gain_loss=0.0,
        average_gain_loss_percentage=0.0,
    )


def make_stock_schema():
    """Helper to create a StockSchema for test assertions."""
    return StockSchema(
        id="10",
        name="Apple Inc.",
        symbol="AAPL",
        shares_number=10.0,
        cost=1500.0,
        prum=150.0,
        today_price=175.0,
        market_value=1750.0,
        gain_loss=250.0,
        gain_loss_percentage=16.67,
        current_repartition=50.0,
        target_repartition=60.0,
        arbitration_threshold=5.0,
        threshold_to_alert=10.0,
    )


SAMPLE_FUND = make_fund_schema()
SAMPLE_FUND_WITH_STOCK = make_fund_schema(stocks=[make_stock_schema()])


# ── Fund Endpoints ────────────────────────────────────────────────


class TestFundEndpoints:
    """Tests for /funds endpoints."""

    def test_get_all_funds(self, client, mocker):
        """
        Given: Two funds exist
        When: GET /funds
        Then: Returns 200 with list of funds
        """
        mocker.patch(
            "src.routes.funds.FundService.get_all",
            return_value=[SAMPLE_FUND, make_fund_schema(fund_id="2", name="Fund 2")],
        )

        response = client.get("/funds")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["fund_name"] == "Test Fund"
        assert data[1]["fund_name"] == "Fund 2"

    def test_get_all_funds_empty(self, client, mocker):
        """
        Given: No funds exist
        When: GET /funds
        Then: Returns 200 with empty list
        """
        mocker.patch("src.routes.funds.FundService.get_all", return_value=[])

        response = client.get("/funds")

        assert response.status_code == 200
        assert response.json() == []

    def test_get_fund_by_id(self, client, mocker):
        """
        Given: Fund with id=1 exists
        When: GET /funds/1
        Then: Returns 200 with fund data including stocks
        """
        mocker.patch(
            "src.routes.funds.FundService.get_by_id",
            return_value=SAMPLE_FUND_WITH_STOCK,
        )

        response = client.get("/funds/1")

        assert response.status_code == 200
        data = response.json()
        assert data["fund_name"] == "Test Fund"
        assert len(data["stocks"]) == 1
        assert data["stocks"][0]["symbol"] == "AAPL"

    def test_get_fund_not_found(self, client, mocker):
        """
        Given: No fund with id=999
        When: GET /funds/999
        Then: Returns 404
        """
        mocker.patch("src.routes.funds.FundService.get_by_id", return_value=None)

        response = client.get("/funds/999")

        assert response.status_code == 404
        assert response.json()["detail"] == "Fund not found"

    def test_create_fund(self, client, mocker):
        """
        Given: Valid fund name
        When: POST /funds
        Then: Returns 201 with created fund
        """
        mocker.patch("src.routes.funds.FundService.create", return_value=SAMPLE_FUND)

        response = client.post("/funds", json={"fund_name": "Test Fund"})

        assert response.status_code == 201
        data = response.json()
        assert data["fund_name"] == "Test Fund"
        assert data["stocks"] == []

    def test_create_fund_missing_name(self, client):
        """
        Given: Missing fund_name in body
        When: POST /funds
        Then: Returns 422 validation error
        """
        response = client.post("/funds", json={})

        assert response.status_code == 422

    def test_update_fund_name(self, client, mocker):
        """
        Given: Fund exists with id=1
        When: PUT /funds/1 with new name
        Then: Returns 200 with updated fund
        """
        updated = make_fund_schema(name="Updated Name")
        mocker.patch("src.routes.funds.FundService.update", return_value=updated)

        response = client.put("/funds/1", json={"fund_name": "Updated Name"})

        assert response.status_code == 200
        assert response.json()["fund_name"] == "Updated Name"

    def test_update_fund_not_found(self, client, mocker):
        """
        Given: No fund with id=999
        When: PUT /funds/999
        Then: Returns 404
        """
        mocker.patch("src.routes.funds.FundService.update", return_value=None)

        response = client.put("/funds/999", json={"fund_name": "X"})

        assert response.status_code == 404
        assert response.json()["detail"] == "Fund not found"

    def test_delete_fund(self, client, mocker):
        """
        Given: Fund exists with id=1
        When: DELETE /funds/1
        Then: Returns 200 with success
        """
        mocker.patch("src.routes.funds.FundService.delete", return_value=True)

        response = client.delete("/funds/1")

        assert response.status_code == 200

    def test_delete_fund_not_found(self, client, mocker):
        """
        Given: No fund with id=999
        When: DELETE /funds/999
        Then: Returns 200 with False
        """
        mocker.patch("src.routes.funds.FundService.delete", return_value=False)

        response = client.delete("/funds/999")

        assert response.status_code == 200
        assert response.json() is False


# ── Stock Endpoints ───────────────────────────────────────────────


class TestStockEndpoints:
    """Tests for /funds/{fund_id}/stocks endpoints."""

    def test_add_stock_to_fund(self, client, mocker):
        """
        Given: Fund exists and valid stock data
        When: POST /funds/1/stocks
        Then: Returns 200 with fund including new stock
        """
        mocker.patch(
            "src.routes.funds.StockService.add",
            return_value=SAMPLE_FUND_WITH_STOCK,
        )

        stock_data = {
            "name": "Apple Inc.",
            "symbol": "AAPL",
            "shares_number": 10.0,
            "cost": 1500.0,
            "current_repartition": 50.0,
            "arbitration_threshold": 5.0,
            "threshold_to_alert": 10.0,
        }

        response = client.post("/funds/1/stocks", json=stock_data)

        assert response.status_code == 200
        data = response.json()
        assert len(data["stocks"]) == 1
        assert data["stocks"][0]["symbol"] == "AAPL"

    def test_add_stock_fund_not_found(self, client, mocker):
        """
        Given: No fund with id=999
        When: POST /funds/999/stocks
        Then: Returns 404
        """
        mocker.patch("src.routes.funds.StockService.add", return_value=None)

        stock_data = {
            "name": "Apple",
            "symbol": "AAPL",
            "shares_number": 10.0,
            "cost": 1500.0,
            "current_repartition": 50.0,
            "arbitration_threshold": 5.0,
            "threshold_to_alert": 10.0,
        }

        response = client.post("/funds/999/stocks", json=stock_data)

        assert response.status_code == 404
        assert response.json()["detail"] == "Fund not found"

    def test_add_stock_missing_fields(self, client):
        """
        Given: Missing required fields in stock data
        When: POST /funds/1/stocks
        Then: Returns 422 validation error
        """
        response = client.post("/funds/1/stocks", json={"symbol": "AAPL"})

        assert response.status_code == 422

    def test_update_stock(self, client, mocker):
        """
        Given: Fund and stock exist
        When: PUT /funds/1/stocks/10
        Then: Returns 200 with updated fund
        """
        mocker.patch(
            "src.routes.funds.StockService.update",
            return_value=SAMPLE_FUND_WITH_STOCK,
        )

        stock_data = {
            "name": "Apple Inc.",
            "symbol": "AAPL",
            "shares_number": 20.0,
            "cost": 3000.0,
            "current_repartition": 60.0,
            "arbitration_threshold": 5.0,
            "threshold_to_alert": 10.0,
        }

        response = client.put("/funds/1/stocks/10", json=stock_data)

        assert response.status_code == 200
        assert response.json()["stocks"][0]["symbol"] == "AAPL"

    def test_update_stock_not_found(self, client, mocker):
        """
        Given: Stock does not exist
        When: PUT /funds/1/stocks/999
        Then: Returns 404
        """
        mocker.patch("src.routes.funds.StockService.update", return_value=None)

        stock_data = {
            "name": "Test",
            "symbol": "TEST",
            "shares_number": 1.0,
            "cost": 100.0,
            "current_repartition": 10.0,
            "arbitration_threshold": 0.0,
            "threshold_to_alert": 0.0,
        }

        response = client.put("/funds/1/stocks/999", json=stock_data)

        assert response.status_code == 404
        assert response.json()["detail"] == "Fund or stock not found"

    def test_remove_stock(self, client, mocker):
        """
        Given: Fund with stock
        When: DELETE /funds/1/stocks/10
        Then: Returns 200 with fund without the stock
        """
        mocker.patch(
            "src.routes.funds.StockService.remove",
            return_value=make_fund_schema(stocks=[]),
        )

        response = client.delete("/funds/1/stocks/10")

        assert response.status_code == 200
        assert response.json()["stocks"] == []

    def test_remove_stock_not_found(self, client, mocker):
        """
        Given: Stock does not exist
        When: DELETE /funds/1/stocks/999
        Then: Returns 404
        """
        mocker.patch("src.routes.funds.StockService.remove", return_value=None)

        response = client.delete("/funds/1/stocks/999")

        assert response.status_code == 404
        assert response.json()["detail"] == "Fund or stock not found"


# ── Stock Search Endpoint ─────────────────────────────────────────


class TestStockSearchEndpoint:
    """Tests for /stocks/search endpoint."""

    def test_search_stocks(self, client, mocker):
        """
        Given: Stocks matching query exist
        When: GET /stocks/search?q=AAPL
        Then: Returns 200 with search results
        """
        mocker.patch(
            "src.routes.stocks.search_symbol",
            return_value=[
                {
                    "symbol": "AAPL",
                    "name": "Apple Inc.",
                    "exchange": "NASDAQ",
                    "price": 175.0,
                    "type": "EQUITY",
                }
            ],
        )

        response = client.get("/stocks/search?q=AAPL")

        assert response.status_code == 200
        data = response.json()
        assert data["query"] == "AAPL"
        assert data["count"] == 1
        assert data["results"][0]["symbol"] == "AAPL"
        assert data["results"][0]["name"] == "Apple Inc."

    def test_search_stocks_empty(self, client, mocker):
        """
        Given: No stocks match query
        When: GET /stocks/search?q=XXXXX
        Then: Returns 200 with empty results
        """
        mocker.patch("src.routes.stocks.search_symbol", return_value=[])

        response = client.get("/stocks/search?q=XXXXX")

        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 0
        assert data["results"] == []

    def test_search_stocks_missing_query(self, client):
        """
        Given: No query parameter
        When: GET /stocks/search
        Then: Returns 422 validation error
        """
        response = client.get("/stocks/search")

        assert response.status_code == 422

    def test_search_stocks_error(self, client, mocker):
        """
        Given: search_symbol raises an exception
        When: GET /stocks/search?q=X
        Then: Returns 500 with error message
        """
        mocker.patch(
            "src.routes.stocks.search_symbol",
            side_effect=Exception("yfinance connection error"),
        )

        response = client.get("/stocks/search?q=X")

        assert response.status_code == 500
        assert "error" in response.json()["detail"].lower()


# ── Transaction Endpoints ─────────────────────────────────────────


def make_transaction_schema(
    tx_id=1,
    asset_id=10,
    asset_symbol="AAPL",
    asset_name="Apple Inc.",
    transaction_type="buy",
    quantity=1.5,
    price=100.0,
    total_cost=150.0,
    order_id=None,
) -> TransactionSchema:
    """Helper to create a TransactionSchema for test assertions."""
    return TransactionSchema(
        id=tx_id,
        asset_id=asset_id,
        asset_symbol=asset_symbol,
        asset_name=asset_name,
        transaction_type=transaction_type,
        timestamp=datetime(2026, 1, 15, tzinfo=timezone.utc),
        quantity=quantity,
        price=price,
        total_cost=total_cost,
        order_id=order_id,
        created_at=datetime(2026, 1, 15, tzinfo=timezone.utc),
    )


class TestTransactionEndpoints:
    """Tests for /transactions endpoints."""

    def test_get_transactions_returns_200(self, client, mocker):
        """
        Given: No transactions
        When: GET /transactions
        Then: Returns 200 with empty list
        """
        mocker.patch(
            "src.routes.transactions.TransactionService.get_all",
            return_value=[],
        )

        response = client.get("/transactions")

        assert response.status_code == 200
        assert response.json() == []

    def test_get_transactions_with_fund_id(self, client, mocker):
        """
        Given: fund_id query param
        When: GET /transactions?fund_id=1
        Then: TransactionService.get_all called with fund_id=1
        """
        mock_get_all = mocker.patch(
            "src.routes.transactions.TransactionService.get_all",
            return_value=[],
        )

        client.get("/transactions?fund_id=1")

        mock_get_all.assert_called_once_with(fund_id=1, asset_id=None, limit=100)

    def test_get_transactions_with_limit(self, client, mocker):
        """
        Given: limit query param
        When: GET /transactions?limit=10
        Then: TransactionService.get_all called with limit=10
        """
        mock_get_all = mocker.patch(
            "src.routes.transactions.TransactionService.get_all",
            return_value=[],
        )

        client.get("/transactions?limit=10")

        mock_get_all.assert_called_once_with(fund_id=None, asset_id=None, limit=10)

    def test_get_transactions_returns_transaction_list(self, client, mocker):
        """
        Given: Two transactions exist
        When: GET /transactions
        Then: Returns 200 with list of 2 transactions in JSON
        """
        tx1 = make_transaction_schema(tx_id=1, asset_symbol="AAPL", total_cost=150.0)
        tx2 = make_transaction_schema(
            tx_id=2, asset_symbol="ETH", transaction_type="sell", total_cost=500.0
        )
        mocker.patch(
            "src.routes.transactions.TransactionService.get_all",
            return_value=[tx1, tx2],
        )

        response = client.get("/transactions")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["asset_symbol"] == "AAPL"
        assert data[0]["total_cost"] == 150.0
        assert data[1]["asset_symbol"] == "ETH"
        assert data[1]["transaction_type"] == "sell"
