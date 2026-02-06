"""
Pytest configuration and fixtures for API tests.

Uses in-memory SQLite for fast, isolated tests.
Each test gets a fresh database state.
"""

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from shared.db.config import Base
from shared.db.models.asset import AssetTable
from shared.db.models.fund import FundTable


@pytest.fixture
def test_engine():
    """Create in-memory SQLite database for each test."""
    engine = create_engine("sqlite:///:memory:")

    # Enable foreign key constraints for SQLite (required for cascade delete)
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(engine)
    return engine


@pytest.fixture
def test_session_factory(test_engine):
    """Create a session factory bound to the test engine."""
    return sessionmaker(bind=test_engine)


@pytest.fixture
def test_session(test_session_factory):
    """Create a session for direct database access in tests."""
    session = test_session_factory()
    yield session
    session.close()


@pytest.fixture
def mock_session_local(mocker, test_session_factory):
    """
    Mock SessionLocal to use test database.

    Patches SessionLocal where it's imported (in the repository modules),
    not where it's defined. This allows repository methods to work with
    the test database.
    """
    # Patch SessionLocal in both fund and stock repository modules
    mocker.patch(
        "src.databases.fund.SessionLocal",
        side_effect=lambda: test_session_factory(),
    )
    mocker.patch(
        "src.databases.stock.SessionLocal",
        side_effect=lambda: test_session_factory(),
    )


@pytest.fixture
def sample_fund(test_session):
    """Create a sample fund for testing."""
    fund = FundTable(name="Test Fund")
    test_session.add(fund)
    test_session.commit()
    test_session.refresh(fund)
    return fund


@pytest.fixture
def sample_stock(test_session, sample_fund):
    """Create a sample stock in a fund."""
    stock = AssetTable(
        fund_id=sample_fund.id,
        name="Apple Inc.",
        symbol="AAPL",
        asset_type="stock",
        shares_number=10.0,
        cost=1500.0,
        current_repartition=50.0,
        target_repartition=60.0,
        arbitration_threshold=5.0,
        threshold_to_alert=10.0,
    )
    test_session.add(stock)
    test_session.commit()
    test_session.refresh(stock)
    return stock


@pytest.fixture
def fund_with_stocks(test_session):
    """Create a fund with multiple stocks."""
    fund = FundTable(name="Portfolio Fund")
    test_session.add(fund)
    test_session.commit()

    stocks = [
        AssetTable(
            fund_id=fund.id,
            name="Apple Inc.",
            symbol="AAPL",
            asset_type="stock",
            shares_number=10.0,
            cost=1500.0,
            current_repartition=30.0,
            arbitration_threshold=5.0,
            threshold_to_alert=10.0,
        ),
        AssetTable(
            fund_id=fund.id,
            name="Microsoft",
            symbol="MSFT",
            asset_type="stock",
            shares_number=5.0,
            cost=2000.0,
            current_repartition=40.0,
            arbitration_threshold=5.0,
            threshold_to_alert=10.0,
        ),
        AssetTable(
            fund_id=fund.id,
            name="Google",
            symbol="GOOGL",
            asset_type="stock",
            shares_number=2.0,
            cost=3000.0,
            current_repartition=30.0,
            arbitration_threshold=5.0,
            threshold_to_alert=10.0,
        ),
    ]
    for stock in stocks:
        test_session.add(stock)

    test_session.commit()
    test_session.refresh(fund)
    return fund
