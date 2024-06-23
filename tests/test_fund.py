import pytest

from src.fund import Fund
from src.stock import Stock


class TestFund:
    def test_instansitate_empty_fund_should_have_total_amount_0(self):
        # Given
        expected_total_amount = 0.0

        # When
        actual_fund = Fund("My Fund")

        # Then
        assert actual_fund.total_amount == expected_total_amount

    def test_add_new_stock_should_increase_total_amount(self):
        # Given
        fund = Fund("My Fund")
        stock = Stock("AAPL", 1, 107.37, 100.0)
        expected_total_amount = stock.current_amount

        # When
        fund.add_stock(stock)

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
