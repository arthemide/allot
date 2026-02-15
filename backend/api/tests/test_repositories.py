"""
Tests for API repositories (FundRepository and StockRepository).

Tests CRUD operations, selectinload behavior, and cascade deletes.
"""

import pytest

from shared.db.models.asset import AssetTable
from shared.db.models.fund import FundTable
from src.databases.fund import FundRepository
from src.databases.stock import StockRepository
from src.models.pydantic.schema import StockSchema


class TestFundRepository:
    """Tests for FundRepository CRUD operations."""

    def test_should_return_empty_list_when_no_funds(self, mock_session_local):
        """
        Should return empty list when no funds exist.

        Given: Empty database with no funds
        When: Getting all funds
        Then: Returns empty list
        """
        # Given
        # (empty database from fixture)

        # When
        result = FundRepository.get_all()

        # Then
        assert result == []

    def test_should_return_funds_with_stocks(
        self, mock_session_local, fund_with_stocks
    ):
        """
        Should return all funds with their stocks loaded.

        Given: Database with fund containing stocks
        When: Getting all funds
        Then: Returns funds with stocks via selectinload
        """
        # Given
        # (fund_with_stocks fixture creates fund with 3 stocks)

        # When
        result = FundRepository.get_all()

        # Then
        assert len(result) == 1
        assert result[0].name == "Portfolio Fund"
        assert len(result[0].assets) == 3

    def test_should_return_fund_by_id(self, mock_session_local, sample_fund):
        """
        Should return fund by ID with stocks loaded.

        Given: Database with existing fund
        When: Getting fund by ID
        Then: Returns fund with correct data
        """
        # Given
        fund_id = sample_fund.id

        # When
        result = FundRepository.get_by_id(fund_id)

        # Then
        assert result is not None
        assert result.id == fund_id
        assert result.name == "Test Fund"

    def test_should_return_none_when_fund_not_found(self, mock_session_local):
        """
        Should return None when fund doesn't exist.

        Given: Empty database
        When: Getting fund by non-existent ID
        Then: Returns None
        """
        # Given
        # (empty database)

        # When
        result = FundRepository.get_by_id(99999)

        # Then
        assert result is None

    def test_should_create_fund(self, mock_session_local):
        """
        Should create a new fund and return it with stocks loaded.

        Given: Valid fund name
        When: Creating new fund
        Then: Returns created fund with empty assets list
        """
        # Given
        fund_name = "New Portfolio"

        # When
        result = FundRepository.create(fund_name)

        # Then
        assert result is not None
        assert result.name == "New Portfolio"
        assert result.id is not None
        assert result.assets == []

    def test_should_update_fund_name(self, mock_session_local, sample_fund):
        """
        Should update fund name and return updated fund.

        Given: Existing fund
        When: Updating fund name
        Then: Returns fund with new name
        """
        # Given
        fund_id = sample_fund.id

        # When
        result = FundRepository.update(fund_id, name="Updated Name")

        # Then
        assert result is not None
        assert result.name == "Updated Name"

    def test_should_return_none_when_updating_non_existent_fund(
        self, mock_session_local
    ):
        """
        Should return None when updating non-existent fund.

        Given: Empty database
        When: Updating non-existent fund
        Then: Returns None
        """
        # Given
        # (empty database)

        # When
        result = FundRepository.update(99999, name="New Name")

        # Then
        assert result is None

    def test_should_delete_fund(self, mock_session_local, sample_fund, test_session):
        """
        Should delete fund and return True.

        Given: Existing fund
        When: Deleting fund
        Then: Returns True and fund is removed from database
        """
        # Given
        fund_id = sample_fund.id

        # When
        result = FundRepository.delete(fund_id)

        # Then
        assert result is True
        # Expire cache to see actual DB state
        test_session.expire_all()
        deleted = test_session.get(FundTable, fund_id)
        assert deleted is None

    def test_should_cascade_delete_stocks_when_fund_deleted(
        self, mock_session_local, fund_with_stocks, test_session
    ):
        """
        Should cascade delete stocks when fund is deleted.

        Given: Fund with associated stocks
        When: Deleting fund
        Then: All stocks are also deleted
        """
        # Given
        fund_id = fund_with_stocks.id
        stock_ids = [s.id for s in fund_with_stocks.assets]

        # When
        FundRepository.delete(fund_id)

        # Then
        # Expire cache to see actual DB state
        test_session.expire_all()
        for stock_id in stock_ids:
            stock = test_session.get(AssetTable, stock_id)
            assert stock is None


class TestStockRepository:
    """Tests for StockRepository CRUD operations."""

    def test_should_add_stock_to_fund(self, mock_session_local, sample_fund):
        """
        Should add stock to fund and return fund with stocks.

        Given: Existing fund and valid stock data
        When: Adding stock to fund
        Then: Returns fund with new stock added
        """
        # Given
        stock_data = StockSchema(
            name="Tesla",
            symbol="TSLA",
            shares_number=5.0,
            cost=1000.0,
            current_repartition=25.0,
            target_repartition=30.0,
            arbitration_threshold=5.0,
            threshold_to_alert=10.0,
        )

        # When
        result = StockRepository.add(sample_fund.id, stock_data)

        # Then
        assert result is not None
        assert len(result.assets) == 1
        assert result.assets[0].symbol == "TSLA"
        assert result.assets[0].shares_number == 5.0

    def test_should_raise_error_when_adding_to_invalid_fund(self, mock_session_local):
        """
        Should raise IntegrityError when adding stock to non-existent fund.

        Given: Non-existent fund ID
        When: Adding stock
        Then: Raises IntegrityError due to foreign key constraint
        """
        # Given
        from sqlalchemy.exc import IntegrityError

        stock_data = StockSchema(
            name="Tesla",
            symbol="TSLA",
            shares_number=5.0,
            cost=1000.0,
            current_repartition=25.0,
            arbitration_threshold=0.0,
            threshold_to_alert=0.0,
        )

        # When / Then
        with pytest.raises(IntegrityError):
            StockRepository.add(99999, stock_data)

    def test_should_update_stock(self, mock_session_local, sample_fund, sample_stock):
        """
        Should update stock and return fund with updated stock.

        Given: Existing fund with stock
        When: Updating stock data
        Then: Returns fund with stock updated
        """
        # Given
        updated_data = StockSchema(
            name="Apple Inc.",
            symbol="AAPL",
            shares_number=20.0,
            cost=3000.0,
            current_repartition=60.0,
            arbitration_threshold=5.0,
            threshold_to_alert=10.0,
        )

        # When
        result = StockRepository.update(sample_fund.id, sample_stock.id, updated_data)

        # Then
        assert result is not None
        updated_stock = next(s for s in result.assets if s.id == sample_stock.id)
        assert updated_stock.shares_number == 20.0
        assert updated_stock.cost == 3000.0

    def test_should_return_none_when_updating_non_existent_stock(
        self, mock_session_local, sample_fund
    ):
        """
        Should return None when updating non-existent stock.

        Given: Fund without the target stock
        When: Updating non-existent stock
        Then: Returns None
        """
        # Given
        stock_data = StockSchema(
            name="Test",
            symbol="TEST",
            shares_number=1.0,
            cost=100.0,
            current_repartition=10.0,
            arbitration_threshold=0.0,
            threshold_to_alert=0.0,
        )

        # When
        result = StockRepository.update(sample_fund.id, 99999, stock_data)

        # Then
        assert result is None

    def test_should_remove_stock(
        self, mock_session_local, sample_fund, sample_stock, test_session
    ):
        """
        Should remove stock from fund and return fund.

        Given: Fund with stock
        When: Removing stock
        Then: Returns fund without stock, stock deleted from DB
        """
        # Given
        stock_id = sample_stock.id

        # When
        result = StockRepository.remove(sample_fund.id, stock_id)

        # Then
        assert result is not None
        assert len(result.assets) == 0
        # Expire cache to see actual DB state
        test_session.expire_all()
        deleted = test_session.get(AssetTable, stock_id)
        assert deleted is None

    def test_should_return_none_when_removing_non_existent_stock(
        self, mock_session_local, sample_fund
    ):
        """
        Should return None when removing non-existent stock.

        Given: Fund without the target stock
        When: Removing non-existent stock
        Then: Returns None
        """
        # Given
        # (sample_fund has no stocks)

        # When
        result = StockRepository.remove(sample_fund.id, 99999)

        # Then
        assert result is None
