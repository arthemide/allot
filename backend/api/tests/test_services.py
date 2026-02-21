"""
Tests for FundService and StockService.

Tests business logic with mocked repositories and external calls (yfinance).
"""

import pytest

from src.models.pydantic.schema import FundSchemaUpdate, StockSchema
from src.services.fund import FundService
from src.services.stock import StockService


@pytest.fixture
def mock_repos(mocker):
    """Mock FundRepository and StockRepository."""
    fund_repo = mocker.patch("src.services.fund.FundRepository")
    stock_repo_in_fund = mocker.patch("src.services.fund.StockRepository")
    stock_repo = mocker.patch("src.services.stock.StockRepository")
    fund_repo_in_stock = mocker.patch("src.services.stock.FundRepository")
    return {
        "fund": fund_repo,
        "stock_in_fund": stock_repo_in_fund,
        "stock": stock_repo,
        "fund_in_stock": fund_repo_in_stock,
    }


@pytest.fixture
def mock_yfinance(mocker):
    """Mock yfinance calls used by fund_table_to_pydantic and StockService."""
    mocker.patch("src.services.utils.get_stock_price", return_value=150.0)
    mocker.patch("src.services.stock.get_long_name", return_value="Apple Inc.")


@pytest.fixture
def mock_fund_table(mocker):
    """Create a simple object that mimics FundTable with real attributes (not Mock)."""
    from types import SimpleNamespace

    def _create(name="Test Fund", fund_id=1, assets=None):
        if assets is None:
            asset = SimpleNamespace(
                id=10,
                name="Apple Inc.",
                symbol="AAPL",
                shares_number=10.0,
                cost=1500.0,
                current_repartition=50.0,
                target_repartition=60.0,
                arbitration_threshold=5.0,
                threshold_to_alert=10.0,
            )
            assets = [asset]

        # Create fund with real attributes
        fund = SimpleNamespace(
            id=fund_id, name=name, created_at=None, updated_at=None, assets=assets
        )
        return fund

    return _create


class TestFundService:
    """Tests for FundService business logic."""

    def test_get_all_returns_pydantic_models(
        self, mock_repos, mock_yfinance, mock_fund_table
    ):
        """
        Given: Two funds exist in the database
        When: Getting all funds
        Then: Returns list of FundSchema pydantic models
        """
        # Given
        mock_repos["fund"].get_all.return_value = [
            mock_fund_table(name="Fund 1", fund_id=1),
            mock_fund_table(name="Fund 2", fund_id=2),
        ]

        # When
        result = FundService.get_all()

        # Then
        assert len(result) == 2
        assert result[0].fund_name == "Fund 1"
        assert result[1].fund_name == "Fund 2"
        mock_repos["fund"].get_all.assert_called_once()

    def test_get_all_returns_empty_list(self, mock_repos):
        """
        Given: No funds in database
        When: Getting all funds
        Then: Returns empty list
        """
        # Given
        mock_repos["fund"].get_all.return_value = []

        # When
        result = FundService.get_all()

        # Then
        assert result == []

    def test_get_by_id_returns_fund(self, mock_repos, mock_yfinance, mock_fund_table):
        """
        Given: Fund exists with given ID
        When: Getting fund by ID
        Then: Returns FundSchema with correct data
        """
        # Given
        mock_repos["fund"].get_by_id.return_value = mock_fund_table()

        # When
        result = FundService.get_by_id("1")

        # Then
        assert result is not None
        assert result.fund_name == "Test Fund"
        assert len(result.stocks) == 1
        assert result.stocks[0].symbol == "AAPL"
        mock_repos["fund"].get_by_id.assert_called_once_with("1")

    def test_get_by_id_returns_none_when_not_found(self, mock_repos):
        """
        Given: No fund with given ID
        When: Getting fund by ID
        Then: Returns None
        """
        # Given
        mock_repos["fund"].get_by_id.return_value = None

        # When
        result = FundService.get_by_id("999")

        # Then
        assert result is None

    def test_create_returns_new_fund(self, mock_repos, mock_yfinance, mock_fund_table):
        """
        Given: Valid fund name
        When: Creating a new fund
        Then: Returns created FundSchema
        """
        # Given
        created_fund = mock_fund_table(name="New Fund", assets=[])
        mock_repos["fund"].create.return_value = created_fund

        # When
        result = FundService.create("New Fund")

        # Then
        assert result.fund_name == "New Fund"
        assert result.stocks == []
        mock_repos["fund"].create.assert_called_once_with("New Fund")

    def test_delete_returns_true(self, mock_repos):
        """
        Given: Fund exists
        When: Deleting fund
        Then: Returns True
        """
        # Given
        mock_repos["fund"].delete.return_value = True

        # When
        result = FundService.delete("1")

        # Then
        assert result is True
        mock_repos["fund"].delete.assert_called_once_with("1")

    def test_delete_returns_false_when_not_found(self, mock_repos):
        """
        Given: Fund does not exist
        When: Deleting fund
        Then: Returns False
        """
        # Given
        mock_repos["fund"].delete.return_value = False

        # When
        result = FundService.delete("999")

        # Then
        assert result is False

    def test_update_replaces_stocks(
        self, mock_repos, mock_yfinance, mock_fund_table, mocker
    ):
        """
        Given: Fund with existing stocks and update with new stocks
        When: Updating fund
        Then: Old stocks are removed and new stocks are added
        """
        # Given
        from types import SimpleNamespace

        old_asset = SimpleNamespace(id=10)
        existing_fund = mock_fund_table(assets=[old_asset])
        updated_fund = mock_fund_table(name="Test Fund", assets=[])

        # 1st call: returns fund with old asset, 2nd call: returns fund after cleanup
        mock_repos["fund"].get_by_id.side_effect = [existing_fund, updated_fund]

        new_stock = StockSchema(
            name="Tesla",
            symbol="TSLA",
            shares_number=5.0,
            cost=1000.0,
            current_repartition=25.0,
            arbitration_threshold=5.0,
            threshold_to_alert=10.0,
        )
        updates = FundSchemaUpdate(stocks=[new_stock])

        # When
        result = FundService.update("1", updates)

        # Then: old stock removed, new stock added
        mock_repos["stock_in_fund"].remove.assert_called_once_with("1", 10)
        mock_repos["stock_in_fund"].add.assert_called_once()
        add_call = mock_repos["stock_in_fund"].add.call_args
        assert add_call[0][0] == "1"
        assert add_call[0][1]["symbol"] == "TSLA"
        assert result is not None

    def test_update_name_only(self, mock_repos, mock_yfinance, mock_fund_table):
        """
        Given: Update with only fund name (no stocks)
        When: Updating fund
        Then: Only name is updated, stocks untouched
        """
        # Given
        updated_fund = mock_fund_table(name="New Name")
        mock_repos["fund"].update.return_value = updated_fund
        updates = FundSchemaUpdate(fund_name="New Name")

        # When
        result = FundService.update("1", updates)

        # Then
        assert result.fund_name == "New Name"
        mock_repos["fund"].update.assert_called_once_with("1", "New Name")
        mock_repos["stock_in_fund"].remove.assert_not_called()
        mock_repos["stock_in_fund"].add.assert_not_called()

    def test_update_returns_none_when_fund_not_found(self, mock_repos):
        """
        Given: Fund does not exist
        When: Updating fund with stocks
        Then: Returns None
        """
        # Given
        mock_repos["fund"].get_by_id.return_value = None
        new_stock = StockSchema(
            name="Tesla",
            symbol="TSLA",
            shares_number=5.0,
            cost=1000.0,
            current_repartition=25.0,
            arbitration_threshold=5.0,
            threshold_to_alert=10.0,
        )
        updates = FundSchemaUpdate(stocks=[new_stock])

        # When
        result = FundService.update("1", updates)

        # Then
        assert result is None


class TestStockService:
    """Tests for StockService business logic."""

    def test_add_stock_to_fund(
        self, mock_repos, mock_yfinance, mock_fund_table, mocker
    ):
        """
        Given: Fund exists and valid stock data
        When: Adding stock to fund
        Then: Stock is added via repository and fund is returned
        """
        # Given
        fund = mock_fund_table()
        mock_repos["fund_in_stock"].get_by_id.return_value = fund
        mock_repos["stock"].add.return_value = fund

        stock = StockSchema(
            name="Apple Inc.",
            symbol="AAPL",
            shares_number=10.0,
            cost=1500.0,
            current_repartition=50.0,
            arbitration_threshold=5.0,
            threshold_to_alert=10.0,
        )

        # When
        result = StockService.add("1", stock)

        # Then
        assert result is not None
        assert result.fund_name == "Test Fund"
        mock_repos["stock"].add.assert_called_once_with("1", stock)

    def test_add_stock_fetches_name_when_missing(
        self, mock_repos, mock_yfinance, mock_fund_table
    ):
        """
        Given: Stock without name
        When: Adding stock
        Then: Name is fetched from yfinance
        """
        # Given
        fund = mock_fund_table()
        mock_repos["fund_in_stock"].get_by_id.return_value = fund
        mock_repos["stock"].add.return_value = fund

        stock = StockSchema(
            name=None,
            symbol="AAPL",
            shares_number=10.0,
            cost=1500.0,
            current_repartition=50.0,
            arbitration_threshold=5.0,
            threshold_to_alert=10.0,
        )

        # When
        StockService.add("1", stock)

        # Then
        assert stock.name == "Apple Inc."

    def test_add_stock_returns_none_when_fund_not_found(self, mock_repos):
        """
        Given: Fund does not exist
        When: Adding stock
        Then: Returns None without calling repository
        """
        # Given
        mock_repos["fund_in_stock"].get_by_id.return_value = None

        stock = StockSchema(
            name="Tesla",
            symbol="TSLA",
            shares_number=5.0,
            cost=1000.0,
            current_repartition=25.0,
            arbitration_threshold=5.0,
            threshold_to_alert=10.0,
        )

        # When
        result = StockService.add("1", stock)

        # Then
        assert result is None
        mock_repos["stock"].add.assert_not_called()

    def test_update_stock(self, mock_repos, mock_yfinance, mock_fund_table):
        """
        Given: Fund and stock exist
        When: Updating stock
        Then: Returns updated fund via repository
        """
        # Given
        fund = mock_fund_table()
        mock_repos["stock"].update.return_value = fund

        stock = StockSchema(
            name="Apple Inc.",
            symbol="AAPL",
            shares_number=20.0,
            cost=3000.0,
            current_repartition=60.0,
            arbitration_threshold=5.0,
            threshold_to_alert=10.0,
        )

        # When
        result = StockService.update("1", "10", stock)

        # Then
        assert result is not None
        mock_repos["stock"].update.assert_called_once_with("1", "10", stock)

    def test_update_stock_returns_none_when_not_found(self, mock_repos):
        """
        Given: Stock does not exist
        When: Updating stock
        Then: Returns None
        """
        # Given
        mock_repos["stock"].update.return_value = None

        stock = StockSchema(
            name="Test",
            symbol="TEST",
            shares_number=1.0,
            cost=100.0,
            current_repartition=10.0,
            arbitration_threshold=0.0,
            threshold_to_alert=0.0,
        )

        # When
        result = StockService.update("1", "999", stock)

        # Then
        assert result is None

    def test_remove_stock(self, mock_repos, mock_yfinance, mock_fund_table):
        """
        Given: Fund with stock
        When: Removing stock
        Then: Returns fund without stock
        """
        # Given
        fund = mock_fund_table(assets=[])
        mock_repos["stock"].remove.return_value = fund

        # When
        result = StockService.remove("1", "10")

        # Then
        assert result is not None
        assert result.stocks == []
        mock_repos["stock"].remove.assert_called_once_with("1", "10")

    def test_remove_stock_returns_none_when_not_found(self, mock_repos):
        """
        Given: Stock does not exist
        When: Removing stock
        Then: Returns None
        """
        # Given
        mock_repos["stock"].remove.return_value = None

        # When
        result = StockService.remove("1", "999")

        # Then
        assert result is None
