"""
Tests for PurchaseTracker.

Tests purchase tracking, PRUM calculation, statistics retrieval,
and error handling with database operations.
"""

from decimal import Decimal

import pytest

from dca.purchase_tracker import PurchaseTracker


@pytest.fixture
def mock_transaction_repo(mocker):
    """
    Mock TransactionRepository for testing.

    Given: Need to test PurchaseTracker without real database
    When: Tests are executed
    Then: All DB operations are mocked
    """
    mock_repo = mocker.patch("dca.purchase_tracker.TransactionRepository")
    mock_asset = mocker.Mock()
    mock_asset.id = 1
    mock_asset.symbol = "ETHUSDC"
    mock_repo.get_or_create_asset.return_value = mock_asset
    return mock_repo


class TestPurchaseTrackerInit:
    """Tests for PurchaseTracker initialization."""

    def test_should_create_asset_on_init(self, mock_transaction_repo):
        """
        Should initialize and create/get asset from database.

        Given: Valid symbol and asset configuration
        When: Creating a new PurchaseTracker
        Then: Asset is created/retrieved from DB with correct parameters
        """
        # Given
        # (mock already configured in fixture)

        # When
        tracker = PurchaseTracker(
            symbol="ETHUSDC",
            asset_name="Ethereum",
            fund_id=None,
            base_prum=2500.0,
            base_quantity=1.5,
        )

        # Then
        mock_transaction_repo.get_or_create_asset.assert_called_once_with(
            symbol="ETHUSDC",
            name="Ethereum",
            fund_id=None,
            base_prum=Decimal("2500.0"),
            historical_quantity=Decimal("1.5"),
            currency="USD"
        )
        assert tracker.symbol == "ETHUSDC"
        assert tracker.base_prum == Decimal("2500.0")
        assert tracker.base_quantity == Decimal("1.5")

    def test_should_init_without_base_prum(self, mock_transaction_repo):
        """
        Should initialize without base PRUM for first time tracking.

        Given: No base PRUM or quantity provided
        When: Creating a new PurchaseTracker
        Then: Defaults to None PRUM and zero quantity
        """
        # Given
        # (mock already configured in fixture)

        # When
        tracker = PurchaseTracker(
            symbol="BTCUSDC",
            asset_name="Bitcoin",
        )

        # Then
        assert tracker.base_prum is None
        assert tracker.base_quantity == Decimal("0")

    def test_should_raise_on_db_error_during_init(self, mock_transaction_repo):
        """
        Should raise exception when database initialization fails.

        Given: Database returns an error
        When: Attempting to create PurchaseTracker
        Then: Exception is propagated
        """
        # Given
        mock_transaction_repo.get_or_create_asset.side_effect = Exception("DB error")

        # When / Then
        with pytest.raises(Exception, match="DB error"):
            PurchaseTracker(symbol="ETHUSDC", asset_name="Ethereum")


class TestAddPurchase:
    """Tests for adding purchases."""

    def test_should_record_purchase_in_database(self, mock_transaction_repo, mocker):
        """
        Should record purchase transaction in database.

        Given: Valid purchase details
        When: Adding a purchase
        Then: Transaction is recorded with correct parameters
        """
        # Given
        tracker = PurchaseTracker(symbol="ETHUSDC", asset_name="Ethereum")
        mock_transaction = mocker.Mock()
        mock_transaction.id = 42
        mock_transaction_repo.add_transaction.return_value = mock_transaction

        # When
        tracker.add_purchase(
            quantity=Decimal("0.01"),
            price=Decimal("3000.0"),
            total_cost=Decimal("30.0"),
            order_id="12345",
            timestamp="2024-01-15T10:00:00Z",
        )

        # Then
        mock_transaction_repo.add_transaction.assert_called_once()
        call_kwargs = mock_transaction_repo.add_transaction.call_args[1]
        assert call_kwargs["asset_id"] == 1
        assert call_kwargs["transaction_type"] == "buy"
        assert call_kwargs["quantity"] == Decimal("0.01")
        assert call_kwargs["price"] == Decimal("3000.0")
        assert call_kwargs["total_cost"] == Decimal("30.0")
        assert call_kwargs["order_id"] == "12345"

    def test_should_accept_purchase_without_timestamp(
        self, mock_transaction_repo, mocker
    ):
        """
        Should accept purchase without timestamp, defaulting to now.

        Given: Purchase details without timestamp
        When: Adding a purchase
        Then: Transaction is recorded with None timestamp (DB uses now)
        """
        # Given
        tracker = PurchaseTracker(symbol="ETHUSDC", asset_name="Ethereum")
        mock_transaction_repo.add_transaction.return_value = mocker.Mock(id=1)

        # When
        tracker.add_purchase(
            quantity=Decimal("0.01"),
            price=Decimal("3000.0"),
            total_cost=Decimal("30.0"),
        )

        # Then
        call_kwargs = mock_transaction_repo.add_transaction.call_args[1]
        assert call_kwargs["timestamp"] is None

    def test_should_raise_on_recording_error(self, mock_transaction_repo):
        """
        Should raise exception when recording fails.

        Given: Database write fails
        When: Attempting to add purchase
        Then: Exception is propagated
        """
        # Given
        tracker = PurchaseTracker(symbol="ETHUSDC", asset_name="Ethereum")
        mock_transaction_repo.add_transaction.side_effect = Exception("Write error")

        # When / Then
        with pytest.raises(Exception, match="Write error"):
            tracker.add_purchase(
                quantity=Decimal("0.01"),
                price=Decimal("3000.0"),
                total_cost=Decimal("30.0"),
            )


class TestCalculatePrum:
    """Tests for PRUM calculation."""

    def test_should_return_prum_from_repository(self, mock_transaction_repo):
        """
        Should return PRUM value from repository.

        Given: Repository returns valid PRUM
        When: Calculating PRUM
        Then: Returns the PRUM value from repository
        """
        # Given
        tracker = PurchaseTracker(symbol="ETHUSDC", asset_name="Ethereum")
        mock_transaction_repo.calculate_prum.return_value = Decimal("2750.50")

        # When
        result = tracker.calculate_prum()

        # Then
        assert result == Decimal("2750.50")
        mock_transaction_repo.calculate_prum.assert_called_once_with("ETHUSDC")

    def test_should_return_none_when_no_purchases(self, mock_transaction_repo):
        """
        Should return None when no purchases recorded.

        Given: No purchases exist in database
        When: Calculating PRUM
        Then: Returns None
        """
        # Given
        tracker = PurchaseTracker(symbol="ETHUSDC", asset_name="Ethereum")
        mock_transaction_repo.calculate_prum.return_value = None

        # When
        result = tracker.calculate_prum()

        # Then
        assert result is None

    def test_should_return_none_on_error(self, mock_transaction_repo):
        """
        Should return None on error for graceful degradation.

        Given: Database error during PRUM calculation
        When: Calculating PRUM
        Then: Returns None instead of raising
        """
        # Given
        tracker = PurchaseTracker(symbol="ETHUSDC", asset_name="Ethereum")
        mock_transaction_repo.calculate_prum.side_effect = Exception("DB error")

        # When
        result = tracker.calculate_prum()

        # Then
        assert result is None


class TestGetStatistics:
    """Tests for statistics retrieval."""

    def test_should_return_statistics_from_repository(self, mock_transaction_repo):
        """
        Should return statistics dictionary from repository.

        Given: Repository returns valid statistics
        When: Getting statistics
        Then: Returns statistics dict with last_updated added
        """
        # Given
        tracker = PurchaseTracker(symbol="ETHUSDC", asset_name="Ethereum")
        mock_transaction_repo.get_asset_statistics.return_value = {
            "prum": "2500.0",
            "transaction_count": 10,
            "transaction_total_quantity": "0.5",
            "transaction_total_cost": "1250.0",
        }

        # When
        result = tracker.get_statistics()

        # Then
        assert result["prum"] == "2500.0"
        assert result["transaction_count"] == 10
        assert "last_updated" in result

    def test_should_return_empty_dict_on_error(self, mock_transaction_repo):
        """
        Should return empty dict on error.

        Given: Database error during statistics retrieval
        When: Getting statistics
        Then: Returns empty dict instead of raising
        """
        # Given
        tracker = PurchaseTracker(symbol="ETHUSDC", asset_name="Ethereum")
        mock_transaction_repo.get_asset_statistics.side_effect = Exception("DB error")

        # When
        result = tracker.get_statistics()

        # Then
        assert result == {}


class TestGetRecentPurchases:
    """Tests for recent purchases retrieval."""

    def test_should_return_recent_purchases_as_list(
        self, mock_transaction_repo, mocker
    ):
        """
        Should return recent purchases as list of dictionaries.

        Given: Repository returns list of transactions
        When: Getting recent purchases
        Then: Returns formatted list of purchase dicts
        """
        # Given
        tracker = PurchaseTracker(symbol="ETHUSDC", asset_name="Ethereum")

        mock_tx1 = mocker.Mock()
        mock_tx1.timestamp.isoformat.return_value = "2024-01-15T10:00:00"
        mock_tx1.quantity = Decimal("0.01")
        mock_tx1.price = Decimal("3000.0")
        mock_tx1.total_cost = Decimal("30.0")
        mock_tx1.order_id = "123"

        mock_tx2 = mocker.Mock()
        mock_tx2.timestamp.isoformat.return_value = "2024-01-14T10:00:00"
        mock_tx2.quantity = Decimal("0.02")
        mock_tx2.price = Decimal("2900.0")
        mock_tx2.total_cost = Decimal("58.0")
        mock_tx2.order_id = "122"

        mock_transaction_repo.get_recent_transactions.return_value = [
            mock_tx1,
            mock_tx2,
        ]

        # When
        result = tracker.get_recent_purchases(limit=5)

        # Then
        assert len(result) == 2
        assert result[0]["timestamp"] == "2024-01-15T10:00:00"
        assert result[0]["quantity"] == "0.01"
        assert result[0]["price"] == "3000.0"
        assert result[0]["order_id"] == "123"

    def test_should_return_empty_list_on_error(self, mock_transaction_repo):
        """
        Should return empty list on error.

        Given: Database error during retrieval
        When: Getting recent purchases
        Then: Returns empty list instead of raising
        """
        # Given
        tracker = PurchaseTracker(symbol="ETHUSDC", asset_name="Ethereum")
        mock_transaction_repo.get_recent_transactions.side_effect = Exception(
            "DB error"
        )

        # When
        result = tracker.get_recent_purchases()

        # Then
        assert result == []

    def test_should_pass_limit_to_repository(self, mock_transaction_repo):
        """
        Should pass limit parameter to repository.

        Given: Specific limit requested
        When: Getting recent purchases with limit
        Then: Repository is called with correct limit
        """
        # Given
        tracker = PurchaseTracker(symbol="ETHUSDC", asset_name="Ethereum")
        mock_transaction_repo.get_recent_transactions.return_value = []

        # When
        tracker.get_recent_purchases(limit=3)

        # Then
        mock_transaction_repo.get_recent_transactions.assert_called_with(
            "ETHUSDC", limit=3
        )
