import pytest

from src.fund import Fund
from src.stock import Stock


class TestFund:
    def test_instansitate_empty_fund_should_have_total_amount_0(self):
        # Given
        expected_total_amount = 0.0

        # When
        actual_fund = Fund("Empty Fund")

        # Then
        assert actual_fund.total_amount == expected_total_amount

    def test_should_raise_error_on_repartition_lower_than_zero(self):
        # Given
        fund = Fund("My Fund")

        # When
        with pytest.raises(ValueError) as e:
            fund.check_on_repartition(-1)

        # Then
        assert (
            str(e.value)
            == "The repartition of the fund is greater than 100% (-1).Please adjust the repartition of the stocks."
        )

    def test_should_raise_error_when_symbol_is_not_in_fund(self):
        # Given
        fund = Fund("My Fund")

        # When
        with pytest.raises(ValueError) as e:
            fund.get_stock_from_symbol("AAPL")

        # Then
        assert str(e.value) == "AAPL is not in the fund"

    def test_create_two_funds_one_full_and_one_empty_should_be_normal(self):
        # Given
        actual_full_fund = Fund("Full Fund")
        stock = Stock("AAPL", 1, 107.37, 100.0)
        actual_full_fund.add_stock(stock)
        excepted_number_on_full_fund = 1

        actual_empty_fund = Fund("Empty Fund")
        excepted_number_on_empty_fund = 0

        # Then
        assert len(actual_empty_fund.stocks) == excepted_number_on_empty_fund
        assert len(actual_full_fund.stocks) == excepted_number_on_full_fund

    def test_add_new_stock_should_increase_total_amount(self):
        # Given
        fund = Fund("My Fund")
        stock = Stock("AAPL", 1, 107.37, 100.0)
        expected_total_amount = stock.current_amount

        # When
        fund.add_stock(stock)

        # Then
        assert fund.total_amount == expected_total_amount

    def test_add_two_new_stock_should_increase_total_amount(self):
        # Given
        fund = Fund("My Fund")
        stock_aapl = Stock("AAPL", 1, 107.37, 50)
        stock_googl = Stock("GOOGL", 1, 10.37, 50)
        expected_total_amount = stock_aapl.current_amount + stock_googl.current_amount

        # When
        fund.add_stock(stock_aapl)
        fund.add_stock(stock_googl)

        # Then
        assert fund.total_amount == expected_total_amount

    def test_add_new_stock_should_check_if_repartition_is_correct(self):
        # Given
        fund = Fund("My Fund")
        stock = Stock("AAPL", 1, 107.37, 100.0)
        expected_repartition = 100.0

        # When
        fund.add_stock(stock)

        # Then
        assert fund.total_repartition == expected_repartition

    def test_add_new_stock_already_in_fund_should_raise_an_error(self):
        # Given
        fund = Fund("My Fund")
        stock = Stock("AAPL", 1, 107.37, 100.0)
        fund.add_stock(stock)

        # When
        with pytest.raises(ValueError) as e:
            fund.add_stock(stock)

        # Then
        assert str(e.value) == "AAPL is already in the fund"

    def test_get_stock_from_symbol(self):
        # Given
        fund = Fund("My Fund")
        expected_stock = Stock("AAPL", 1, 107.37, 100.0)
        fund.add_stock(expected_stock)

        # When
        actual_stock = fund.get_stock_from_symbol("AAPL")

        # Then
        assert actual_stock == expected_stock

    def test_remove_stock_not_on_fund_should_raise_error(self):
        # Given
        fund = Fund("My Fund")
        stock = Stock("AAPL", 1, 107.37, 100.0)

        # When
        with pytest.raises(ValueError) as e:
            fund.remove_stock(stock)

        # Then
        assert str(e.value) == "AAPL is not in the fund"

    def test_remove_stock_should_decrease_total_amount(self):
        # Given
        fund = Fund("My Fund")
        stock = Stock("AAPL", 1, 107.37, 100.0)
        fund.add_stock(stock)
        expected_total_amount = 0.0

        # When
        fund.remove_stock(stock)

        # Then
        assert fund.total_amount == expected_total_amount
