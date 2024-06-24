import pytest

from src.stock import Stock


class TestStock:
    def test_get_stock_price(self):
        # Given
        stock_symbol = "AAPL"

        # When
        stock = Stock(stock_symbol)

        # Then
        assert stock.current_price > 0

    def test_get_stock_price_invalid_symbol(self, caplog):
        # Given
        stock_symbol = "INVALID"
        error_expected = f"{stock_symbol}: No data found, symbol may be delisted"

        # When
        with pytest.raises(UserWarning):
            Stock(stock_symbol)

        # Then
        assert error_expected in caplog.text

    def test_get_stock_price_invalid_period(self, caplog):
        # Given
        stock_symbol = "0P00000QUN.F"
        error_expected = (
            f"{stock_symbol}: Period '1d' is invalid, must be one of ['1mo', '3mo', '6mo', 'ytd', '1y', '2y', "
            "'5y', '10y', 'max']"
        )

        # When
        with pytest.raises(UserWarning):
            Stock(stock_symbol)

        # Then
        assert error_expected in caplog.messages[0]

    def test_should_well_calculated_profit(self, mocker):
        # Given
        stock_symbol = "AAPL"
        parts_number = 107.37
        prum = 50.58

        expected_current_amount = 8562.76
        expected_current_profit = 3131.98

        # When
        with mocker.patch("src.stock.Stock.get_stock_price", return_value=79.75):
            actual_stock = Stock(stock_symbol, parts_number, prum)

            # Then
            assert actual_stock.current_amount == expected_current_amount
            assert actual_stock.current_profit == expected_current_profit

    def test_should_raise_error_on_invalid_repartition(self):
        # Given
        stock_symbol = "AAPL"
        invalid_repartition = 101

        # When
        with pytest.raises(ValueError) as exc_info:
            Stock(stock_symbol, repartition=invalid_repartition)

        # Then
        assert str(exc_info.value) == "The repartition must be between 0 and 100"