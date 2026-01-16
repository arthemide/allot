"""
Simple pytest fixtures for bot tests.
Keep it simple - mock external dependencies.
"""
import os
import pytest
from decimal import Decimal

from dca.models import Kline

@pytest.fixture(scope="session", autouse=True)
def set_env():
    os.environ["BINANCE_API_KEY"] = ""

@pytest.fixture
def mock_binance_client(mocker):
    """Mock Binance client for testing."""
    client = mocker.Mock()
    client.get_symbol_price = mocker.Mock(return_value=Decimal("3000.0"))
    client.get_asset_balance = mocker.Mock()
    client.get_klines = mocker.Mock()
    return client


@pytest.fixture
def mock_purchase_tracker(mocker):
    """Mock purchase tracker for testing."""
    tracker = mocker.Mock()
    tracker.calculate_prum = mocker.Mock(return_value=Decimal("2000.0"))
    tracker.add_purchase = mocker.Mock()
    return tracker


def create_kline(open_price: float, close_price: float) -> Kline:
    """Helper to create a kline for testing."""
    return Kline(
        open_time=0,
        open=Decimal(str(open_price)),
        high=Decimal(str(max(open_price, close_price))),
        low=Decimal(str(min(open_price, close_price))),
        close=Decimal(str(close_price)),
        volume=Decimal("100"),
        close_time=1
    )
