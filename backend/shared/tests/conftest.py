"""
Pytest configuration and fixtures for shared package tests.
Uses in-memory SQLite for fast tests.
"""

from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from shared.db.config import Base
from shared.db.models.asset import AssetTable
from shared.db.models.fund import FundTable


@pytest.fixture(scope="session")
def test_engine():
    """Create in-memory SQLite database for tests."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return engine


@pytest.fixture
def test_session(test_engine):
    """Create a new database session for each test with proper isolation."""
    connection = test_engine.connect()
    transaction = connection.begin()
    TestSessionLocal = sessionmaker(bind=connection)
    session = TestSessionLocal()

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def sample_asset(test_session):
    """Create a sample crypto asset for testing."""
    asset = AssetTable(
        symbol="ETHUSDC",
        name="Ethereum",
        asset_type="crypto",
        shares_number=1.0,  # Historical quantity
        cost=2000.0,  # Historical cost
        base_prum=Decimal("2000.0"),  # Historical PRUM
        current_repartition=0.0,
        target_repartition=0.0,
        arbitration_threshold=0.0,
        threshold_to_alert=0.0,
        fund_id=None,
    )
    test_session.add(asset)
    test_session.commit()
    test_session.refresh(asset)
    return asset


@pytest.fixture
def sample_fund(test_session):
    """Create a sample fund for testing."""
    fund = FundTable(name="Test Fund")
    test_session.add(fund)
    test_session.commit()
    test_session.refresh(fund)
    return fund
