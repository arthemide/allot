"""
Tests for TransactionRepository - focusing on PRUM calculation.
Keep it simple: test critical paths without overengineering.
"""

from datetime import datetime
from decimal import Decimal

from shared.db.models.asset import AssetTable
from shared.db.models.transaction import AssetTransactionTable
from shared.db.repositories.transaction import TransactionRepository


class TestPRUMCalculation:
    """Test PRUM (average purchase price) calculation logic."""

    def test_prum_with_no_transactions_returns_base_prum(
        self, test_session, sample_asset
    ):
        """PRUM with only historical data should return base_prum."""
        # Given: asset with base_prum=2000, shares_number=1.0, no transactions

        # When
        prum = TransactionRepository.calculate_prum(
            "ETHUSDC", asset_type="crypto", session=test_session
        )

        # Then: should return base historical PRUM
        assert prum == Decimal("2000.0")

    def test_prum_with_one_transaction(self, test_session, sample_asset):
        """PRUM should be weighted average of historical + new purchase."""
        # Given: Historical 1 ETH @ 2000, buy 1 ETH @ 3000
        transaction = AssetTransactionTable(
            asset_id=sample_asset.id,
            transaction_type="buy",
            timestamp=datetime.now(),
            quantity=Decimal("1.0"),
            price=Decimal("3000.0"),
            total_cost=Decimal("3000.0"),
            order_id="test_order_1",
        )
        test_session.add(transaction)
        test_session.commit()

        # When
        prum = TransactionRepository.calculate_prum(
            "ETHUSDC", asset_type="crypto", session=test_session
        )

        # Then: (1*2000 + 1*3000) / 2 = 2500
        assert prum == Decimal("2500.0")

    def test_prum_with_multiple_transactions(self, test_session, sample_asset):
        """PRUM should handle multiple purchases correctly."""
        # Given: Historical 1 ETH @ 2000
        # Buy 0.5 ETH @ 3000
        # Buy 0.5 ETH @ 3200
        transactions = [
            AssetTransactionTable(
                asset_id=sample_asset.id,
                transaction_type="buy",
                timestamp=datetime.now(),
                quantity=Decimal("0.5"),
                price=Decimal("3000.0"),
                total_cost=Decimal("1500.0"),
                order_id="test_order_1",
            ),
            AssetTransactionTable(
                asset_id=sample_asset.id,
                transaction_type="buy",
                timestamp=datetime.now(),
                quantity=Decimal("0.5"),
                price=Decimal("3200.0"),
                total_cost=Decimal("1600.0"),
                order_id="test_order_2",
            ),
        ]
        test_session.add_all(transactions)
        test_session.commit()

        # When
        prum = TransactionRepository.calculate_prum(
            "ETHUSDC", asset_type="crypto", session=test_session
        )

        # Then: (1*2000 + 1500 + 1600) / (1 + 0.5 + 0.5) = 5100 / 2 = 2550
        assert prum == Decimal("2550.0")

    def test_prum_with_no_historical_data(self, test_session):
        """PRUM should work with no historical data, only transactions."""
        # Given: Create asset without base_prum
        asset = AssetTable(
            symbol="BTCUSDC",
            name="Bitcoin",
            asset_type="crypto",
            shares_number=0.0,
            cost=0.0,
            base_prum=None,  # No historical data
            current_repartition=0.0,
            target_repartition=0.0,
            arbitration_threshold=0.0,
            threshold_to_alert=0.0,
            fund_id=None,
        )
        test_session.add(asset)
        test_session.commit()

        # Add transactions
        transactions = [
            AssetTransactionTable(
                asset_id=asset.id,
                transaction_type="buy",
                timestamp=datetime.now(),
                quantity=Decimal("0.1"),
                price=Decimal("50000.0"),
                total_cost=Decimal("5000.0"),
                order_id="test_order_1",
            ),
            AssetTransactionTable(
                asset_id=asset.id,
                transaction_type="buy",
                timestamp=datetime.now(),
                quantity=Decimal("0.1"),
                price=Decimal("52000.0"),
                total_cost=Decimal("5200.0"),
                order_id="test_order_2",
            ),
        ]
        test_session.add_all(transactions)
        test_session.commit()

        # When
        prum = TransactionRepository.calculate_prum(
            "BTCUSDC", asset_type="crypto", session=test_session
        )

        # Then: (5000 + 5200) / (0.1 + 0.1) = 10200 / 0.2 = 51000
        assert prum == Decimal("51000.0")

    def test_prum_returns_none_for_nonexistent_asset(self, test_session):
        """PRUM should return None if asset doesn't exist."""
        # When
        prum = TransactionRepository.calculate_prum(
            "NONEXISTENT", asset_type="crypto", session=test_session
        )

        # Then
        assert prum is None


class TestAddTransaction:
    """Test adding transactions to assets."""

    def test_add_transaction_creates_record(self, test_session, sample_asset):
        """Adding a transaction should create a database record."""
        # When
        TransactionRepository.add_transaction(
            symbol="ETHUSDC",
            asset_type="crypto",
            transaction_type="buy",
            quantity=Decimal("0.5"),
            price=Decimal("3100.0"),
            total_cost=Decimal("1550.0"),
            order_id="test_order",
            timestamp=datetime.now(),
            session=test_session,
        )

        # Then
        transactions = (
            test_session.query(AssetTransactionTable)
            .filter_by(asset_id=sample_asset.id)
            .all()
        )

        assert len(transactions) == 1
        assert transactions[0].quantity == Decimal("0.5")
        assert transactions[0].price == Decimal("3100.0")

    def test_add_transaction_returns_accessible_attributes_with_own_session(
        self, test_engine
    ):
        """
        Returned transaction must have accessible attributes after session closes.

        Given: An asset exists in the database
        When: add_transaction is called WITHOUT an external session (own session path)
        Then: The returned object's id, quantity, price are accessible (no DetachedInstanceError)

        Regression test for: sqlalche.me/e/20/bhk3
        """
        from unittest.mock import patch

        from sqlalchemy.orm import sessionmaker

        TestSession = sessionmaker(bind=test_engine)

        # Given: create a dedicated asset (committed directly, not via test_session)
        setup_session = TestSession()
        asset = AssetTable(
            symbol="REGR_DETACHED",
            name="Regression Test",
            asset_type="crypto",
            shares_number=0.0,
            cost=0.0,
            base_prum=None,
            current_repartition=0.0,
            target_repartition=0.0,
            arbitration_threshold=0.0,
            threshold_to_alert=0.0,
            fund_id=None,
        )
        setup_session.add(asset)
        setup_session.commit()
        setup_session.refresh(asset)
        asset_id = asset.id
        setup_session.close()

        try:
            with patch(
                "shared.db.repositories.transaction.SessionLocal", TestSession
            ):
                # When: no session parameter = uses own session (the buggy code path)
                transaction = TransactionRepository.add_transaction(
                    asset_id=asset_id,
                    transaction_type="buy",
                    quantity=Decimal("0.01"),
                    price=Decimal("3000.0"),
                    total_cost=Decimal("30.0"),
                    order_id="regression_test_order",
                    timestamp=datetime.now(),
                )

            # Then: accessing attributes must NOT raise DetachedInstanceError
            assert transaction.id is not None
            assert transaction.quantity == Decimal("0.01")
            assert transaction.price == Decimal("3000.0")
            assert transaction.total_cost == Decimal("30.0")
            assert transaction.order_id == "regression_test_order"
        finally:
            # Clean up committed data to avoid leaking to other tests
            cleanup = TestSession()
            cleanup.query(AssetTransactionTable).filter_by(asset_id=asset_id).delete()
            cleanup.query(AssetTable).filter_by(id=asset_id).delete()
            cleanup.commit()
            cleanup.close()

    def test_add_transaction_returns_accessible_attributes_with_provided_session(
        self, test_session, sample_asset
    ):
        """
        Returned transaction must have accessible attributes with provided session.

        Given: An asset exists in the database
        When: add_transaction is called WITH an external session
        Then: The returned object's id, quantity, price are accessible
        """
        # When
        transaction = TransactionRepository.add_transaction(
            asset_id=sample_asset.id,
            transaction_type="buy",
            quantity=Decimal("0.02"),
            price=Decimal("2900.0"),
            total_cost=Decimal("58.0"),
            order_id="test_accessible_attrs",
            timestamp=datetime.now(),
            session=test_session,
        )

        # Then
        assert transaction.id is not None
        assert transaction.quantity == Decimal("0.02")
        assert transaction.price == Decimal("2900.0")
        assert transaction.order_id == "test_accessible_attrs"


class TestGetOrCreateAsset:
    """Test asset creation and retrieval."""

    def test_get_existing_asset(self, test_session, sample_asset):
        """Should retrieve existing asset."""
        # When
        asset = TransactionRepository.get_or_create_asset(
            symbol="ETHUSDC", name="Ethereum", asset_type="crypto", session=test_session
        )

        # Then
        assert asset.id == sample_asset.id
        assert asset.symbol == "ETHUSDC"

    def test_create_new_asset(self, test_session):
        """Should create new asset if it doesn't exist."""
        # When
        asset = TransactionRepository.get_or_create_asset(
            symbol="BTCUSDC",
            name="Bitcoin",
            asset_type="crypto",
            base_prum=Decimal("45000.0"),
            historical_quantity=0.5,
            session=test_session,
        )

        # Then
        assert asset is not None
        assert asset.symbol == "BTCUSDC"
        assert asset.asset_type == "crypto"
        assert asset.base_prum == Decimal("45000.0")
        assert asset.shares_number == 0.5
