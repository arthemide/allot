import pytest

from src.stock import Stock


class TestStock:
    def test_get_stock_price(self):
        # Given
        stock_symbol = "AAPL"

        # When
        stock = Stock(stock_symbol, 107.37, 10, 15, 100, 50, 1)

        # Then
        assert stock.current_price > 0

    def test_get_stock_price_invalid_symbol(self, caplog):
        # Given
        stock_symbol = "INVALID"
        error_expected = f"{stock_symbol}: No data found, symbol may be delisted"

        # When
        with pytest.raises(UserWarning):
            Stock(stock_symbol, 107.37, 10, 15, 100, 50, 1)

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
            Stock(stock_symbol, 107.37, 10, 15, 100, 50, 1)

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
            actual_stock = Stock(
                symbol=stock_symbol,
                parts_number=parts_number,
                prum=prum,
                current_repartition=100,
                target_repartition=100,
                arbitration_threshold=10,
                threshold_to_alert=15,
            )

            # Then
            assert actual_stock.current_amount == expected_current_amount
            assert actual_stock.current_profit == expected_current_profit

    def test_should_raise_error_on_invalid_repartition(self):
        # Given
        stock_symbol = "AAPL"
        invalid_repartition = 101

        # When
        with pytest.raises(ValueError) as exc_info:
            Stock(
                symbol=stock_symbol,
                parts_number=107.37,
                prum=1,
                current_repartition=invalid_repartition,
                target_repartition=100,
                arbitration_threshold=10,
                threshold_to_alert=15,
            )

        # Then
        assert str(exc_info.value) == "The repartition must be between 0 and 100"

    def test_give_zero_should_return_zero_parts_to_move(self):
        # Given
        parts_number = 0

        # When
        stock = Stock(
            symbol="AAPL",
            parts_number=parts_number,
            prum=1,
            current_repartition=100,
            target_repartition=100,
            arbitration_threshold=10,
            threshold_to_alert=15,
            amount_to_move=3,
        )

        # Then
        assert stock.define_parts_to_move() == 0

    def test_give_stock_and_other_obj_equal_should_raise_not_implemented(self):
        # Given
        stock = Stock(
            symbol="AAPL",
            parts_number=3,
            prum=1,
            current_repartition=100,
            target_repartition=100,
            arbitration_threshold=10,
            threshold_to_alert=15,
            amount_to_move=3,
        )
        other = object()  # An instance of a different class
        excepted_error = NotImplemented

        # When
        is_equal = stock.__eq__(other)

        # Then
        assert is_equal == excepted_error
