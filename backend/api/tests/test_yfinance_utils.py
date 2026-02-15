"""
Tests for yfinance utility functions.

All yfinance calls are mocked to avoid external API dependencies.
"""

import pytest

from src.services.yfinance_utils import (
    _get_history_metadata,
    get_long_name,
    get_stock_price,
    search_symbol,
)


@pytest.fixture
def mock_yf(mocker):
    """Mock yfinance module."""
    return mocker.patch("src.services.yfinance_utils.yf")


class TestGetHistoryMetadata:
    """Tests for _get_history_metadata."""

    def test_returns_metadata(self, mock_yf):
        """
        Given: Valid symbol with available data
        When: Getting history metadata
        Then: Returns metadata dict
        """
        # Given
        metadata = {"regularMarketPrice": 150.0, "longName": "Apple Inc."}
        mock_yf.Ticker.return_value.get_history_metadata.return_value = metadata

        # When
        result = _get_history_metadata("AAPL")

        # Then
        assert result == metadata
        mock_yf.Ticker.assert_called_once_with("AAPL")

    def test_returns_none_when_no_data(self, mock_yf):
        """
        Given: Symbol with no data (delisted)
        When: Getting history metadata
        Then: Returns None
        """
        # Given
        mock_yf.Ticker.return_value.get_history_metadata.return_value = None

        # When
        result = _get_history_metadata("DELISTED")

        # Then
        assert result is None


class TestGetStockPrice:
    """Tests for get_stock_price."""

    def test_returns_rounded_price(self, mock_yf):
        """
        Given: Symbol with available price
        When: Getting stock price
        Then: Returns price rounded to 2 decimals
        """
        # Given
        mock_yf.Ticker.return_value.get_history_metadata.return_value = {
            "regularMarketPrice": 150.456
        }

        # When
        result = get_stock_price("AAPL")

        # Then
        assert result == 150.46

    def test_returns_none_when_no_metadata(self, mock_yf):
        """
        Given: Symbol with no metadata
        When: Getting stock price
        Then: Returns None
        """
        # Given
        mock_yf.Ticker.return_value.get_history_metadata.return_value = None

        # When
        result = get_stock_price("DELISTED")

        # Then
        assert result is None


class TestGetLongName:
    """Tests for get_long_name."""

    def test_returns_long_name(self, mock_yf):
        """
        Given: Symbol with available long name
        When: Getting long name
        Then: Returns company long name
        """
        # Given
        mock_yf.Ticker.return_value.get_history_metadata.return_value = {
            "longName": "Apple Inc."
        }

        # When
        result = get_long_name("AAPL")

        # Then
        assert result == "Apple Inc."

    def test_returns_none_when_no_metadata(self, mock_yf):
        """
        Given: Symbol with no metadata
        When: Getting long name
        Then: Returns None
        """
        # Given
        mock_yf.Ticker.return_value.get_history_metadata.return_value = None

        # When
        result = get_long_name("DELISTED")

        # Then
        assert result is None

    def test_returns_none_when_no_long_name_key(self, mock_yf):
        """
        Given: Metadata exists but has no longName key
        When: Getting long name
        Then: Returns None
        """
        # Given
        mock_yf.Ticker.return_value.get_history_metadata.return_value = {
            "shortName": "AAPL"
        }

        # When
        result = get_long_name("AAPL")

        # Then
        assert result is None


class TestSearchSymbol:
    """Tests for search_symbol."""

    def test_returns_results(self, mock_yf):
        """
        Given: Query matching stocks
        When: Searching for symbol
        Then: Returns list of result dicts with correct fields
        """
        # Given
        mock_yf.Search.return_value.quotes = [
            {"symbol": "AAPL", "exchange": "NMS", "quoteType": "EQUITY"},
        ]
        mock_yf.Ticker.return_value.get_history_metadata.return_value = {
            "regularMarketPrice": 150.0,
            "longName": "Apple Inc.",
            "shortName": "AAPL",
        }

        # When
        result = search_symbol("Apple")

        # Then
        assert len(result) == 1
        assert result[0]["symbol"] == "AAPL"
        assert result[0]["name"] == "Apple Inc."
        assert result[0]["exchange"] == "NMS"
        assert result[0]["type"] == "EQUITY"
        assert result[0]["price"] == 150.0

    def test_falls_back_to_short_name(self, mock_yf):
        """
        Given: Quote with no longName but has shortName
        When: Searching for symbol
        Then: Uses shortName as name
        """
        # Given
        mock_yf.Search.return_value.quotes = [
            {"symbol": "TEST", "exchange": "NYSE", "quoteType": "EQUITY"},
        ]
        mock_yf.Ticker.return_value.get_history_metadata.return_value = {
            "regularMarketPrice": 50.0,
            "shortName": "Test Corp",
        }

        # When
        result = search_symbol("Test")

        # Then
        assert result[0]["name"] == "Test Corp"

    def test_falls_back_to_na_when_no_names(self, mock_yf):
        """
        Given: Quote with no longName or shortName
        When: Searching for symbol
        Then: Uses "N/A" as name
        """
        # Given
        mock_yf.Search.return_value.quotes = [
            {"symbol": "???", "exchange": "", "quoteType": ""},
        ]
        mock_yf.Ticker.return_value.get_history_metadata.return_value = {
            "regularMarketPrice": 0.0,
        }

        # When
        result = search_symbol("unknown")

        # Then
        assert result[0]["name"] == "N/A"

    def test_handles_no_metadata(self, mock_yf):
        """
        Given: Quote where metadata returns None
        When: Searching for symbol
        Then: Uses 0.0 price and "N/A" name
        """
        # Given
        mock_yf.Search.return_value.quotes = [
            {"symbol": "DEAD", "exchange": "NYSE", "quoteType": "EQUITY"},
        ]
        mock_yf.Ticker.return_value.get_history_metadata.return_value = None

        # When
        result = search_symbol("dead")

        # Then
        assert result[0]["price"] == 0.0
        assert result[0]["name"] == "N/A"

    def test_respects_max_results(self, mock_yf):
        """
        Given: Many quotes returned
        When: Searching with max_results=2
        Then: Only returns 2 results
        """
        # Given
        mock_yf.Search.return_value.quotes = [
            {"symbol": f"S{i}", "exchange": "", "quoteType": ""} for i in range(10)
        ]
        mock_yf.Ticker.return_value.get_history_metadata.return_value = {
            "regularMarketPrice": 10.0,
            "longName": "Test",
        }

        # When
        result = search_symbol("test", max_results=2)

        # Then
        assert len(result) == 2

    def test_returns_empty_list_on_exception(self, mock_yf):
        """
        Given: yfinance raises an exception
        When: Searching for symbol
        Then: Returns empty list
        """
        # Given
        mock_yf.Search.side_effect = Exception("API error")

        # When
        result = search_symbol("error")

        # Then
        assert result == []

    def test_returns_empty_list_when_no_quotes(self, mock_yf):
        """
        Given: No matching quotes
        When: Searching for symbol
        Then: Returns empty list
        """
        # Given
        mock_yf.Search.return_value.quotes = []

        # When
        result = search_symbol("xyzxyz")

        # Then
        assert result == []
