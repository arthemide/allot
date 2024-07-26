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
            == "The repartition of the fund is not equal to 100% (-1).Please adjust the repartition of the stocks."
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
        stock = Stock("AAPL", 107.37, 1, 100, 100, 10, 15)
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
        stock = Stock(
            symbol="AAPL",
            parts_number=107.37,
            prum=1,
            current_repartition=100,
            target_repartition=100,
            arbitration_threshold=10,
            threshold_to_alert=15,
        )
        expected_total_amount = stock.current_amount

        # When
        fund.add_stock(stock)

        # Then
        assert fund.total_amount == expected_total_amount

    def test_add_two_new_stock_should_increase_total_amount(self):
        # Given
        stock_aapl = Stock("AAPL", 1, 107.37, 50, 50, 10, 15)
        stock_googl = Stock("GOOGL", 1, 107.37, 50, 50, 10, 15)
        expected_total_amount = stock_aapl.current_amount + stock_googl.current_amount

        # When
        fund = Fund("My Fund", [stock_aapl, stock_googl])

        # Then
        assert fund.total_amount == expected_total_amount

    def test_add_new_stock_should_check_if_repartition_is_correct(self):
        # Given
        fund = Fund("My Fund")
        stock = Stock(
            symbol="AAPL",
            parts_number=107.37,
            prum=1,
            current_repartition=100,
            target_repartition=100,
            arbitration_threshold=10,
            threshold_to_alert=15,
        )
        expected_repartition = 100.0

        # When
        fund.add_stock(stock)

        # Then
        assert fund.total_current_repartition == expected_repartition

    def test_add_new_stock_already_in_fund_should_raise_an_error(self):
        # Given
        fund = Fund("My Fund")
        stock = Stock("AAPL", 1, 107.37, 100, 100, 10, 15)
        fund.add_stock(stock)

        # When
        with pytest.raises(ValueError) as e:
            fund.add_stock(stock)

        # Then
        assert str(e.value) == "AAPL is already in the fund"

    def test_get_stock_from_symbol(self):
        # Given
        fund = Fund("My Fund")
        expected_stock = Stock("AAPL", 1, 107.37, 100, 100, 10, 15)
        fund.add_stock(expected_stock)

        # When
        actual_stock = fund.get_stock_from_symbol("AAPL")

        # Then
        assert actual_stock == expected_stock

    def test_remove_stock_not_on_fund_should_raise_error(self):
        # Given
        fund = Fund("My Fund")
        stock = Stock("AAPL", 1, 107.37, 100, 100, 10, 15)

        # When
        with pytest.raises(ValueError) as e:
            fund.remove_stock(stock)

        # Then
        assert str(e.value) == "AAPL is not in the fund"

    def test_remove_stock_should_decrease_total_amount(self):
        # Given
        fund = Fund("My Fund")
        stock = Stock("AAPL", 1, 107.37, 100, 100, 10, 15)
        fund.add_stock(stock)
        expected_total_amount = 0.0

        # When
        fund.remove_stock(stock)

        # Then
        assert fund.total_amount == expected_total_amount

    def test_add_stock_at_construction_of_fund_should_raise_error_if_repartition_is_not_100(
        self,
    ):
        # Given
        stock_aapl = Stock("AAPL", 1, 107.37, 30, 50, 10, 15, 10, 15)
        stock_googl = Stock("GOOGL", 1, 107.37, 50, 50, 10, 15, 10, 15)

        # When
        with pytest.raises(ValueError) as e:
            Fund("My Fund", [stock_aapl, stock_googl])

        # Then
        assert (
            str(e.value)
            == "The repartition of the fund is not equal to 100% (80).Please adjust the repartition of the stocks."
        )

    def test_add_stock_should_well_define_amount_to_move(self, mocker):
        # Given
        fund = Fund("My Fund")
        with mocker.patch("src.stock.Stock.get_stock_price", return_value=3):
            stock_aapl = Stock("AAPL", 1, 107.37, 10, 20, 10, 15)
        with mocker.patch("src.stock.Stock.get_stock_price", return_value=2):
            stock_googl = Stock("GOOGL", 1, 10, 90, 80, 10, 15)
        fund.add_stocks([stock_aapl, stock_googl])
        expected_amount_to_move_for_aapl = 0.5
        expected_amount_to_move_for_googl = -0.5

        # When
        actual_amount_to_move_for_aapl = stock_aapl.amount_to_move
        actual_amount_to_move_for_googl = stock_googl.amount_to_move

        # Then
        assert actual_amount_to_move_for_aapl == expected_amount_to_move_for_aapl
        assert actual_amount_to_move_for_googl == expected_amount_to_move_for_googl

    def test_add_stock_that_go_over_100_per_should_raise_error(self, mocker):
        # Given
        fund = Fund("My Fund")
        with mocker.patch("src.stock.Stock.get_stock_price", return_value=3):
            stock_aapl = Stock("AAPL", 1, 107.37, 100, 100, 10, 15)
        with mocker.patch("src.stock.Stock.get_stock_price", return_value=2):
            stock_googl = Stock("GOOGL", 1, 10, 90, 80, 10, 15)
        fund.add_stock(stock_aapl)

        # When
        with pytest.raises(ValueError) as e:
            fund.add_stock(stock_googl)

        # Then
        assert (
            str(e.value)
            == "The repartition of the fund is not equal to 100% (190).Please adjust the repartition of the stocks."
        )

    def test_add_stock_that_go_over_100_per_should_return_old_fund(self, mocker):
        # Given
        fund = Fund("My Fund")
        with mocker.patch("src.stock.Stock.get_stock_price", return_value=3):
            stock_aapl = Stock("AAPL", 1, 107.37, 100, 100, 10, 15)
        with mocker.patch("src.stock.Stock.get_stock_price", return_value=2):
            stock_googl = Stock("GOOGL", 1, 10, 90, 80, 10, 15)
        fund.add_stock(stock_aapl)

        # When
        with pytest.raises(ValueError):
            fund.add_stock(stock_googl)

        # Then
        assert len(fund.stocks) == 1
        assert fund.total_amount == stock_aapl.current_amount

    def test_give_stock_should_calculate_right_part_to_move(self, mocker):
        # Given
        fund = Fund("My Fund")
        with mocker.patch("src.stock.Stock.get_stock_price", return_value=3):
            stock_aapl = Stock("AAPL", 1, 107.37, 80, 20, 10, 15)
        with mocker.patch("src.stock.Stock.get_stock_price", return_value=2):
            stock_googl = Stock("GOOGL", 1, 10, 20, 80, 10, 15)
        excepted_parts_to_move = 3.0

        # When
        fund.add_stocks([stock_googl, stock_aapl])

        # Then
        assert stock_googl.parts_to_move == excepted_parts_to_move

    def test_give_stock_should_not_raise_error_for_parts_to_move(self, mocker):
        # Given
        fund = Fund("My Fund")
        with mocker.patch("src.stock.Stock.get_stock_price", return_value=3):
            stock_aapl = Stock("AAPL", 1.0, 107.37, 100, 100, 10, 15)
        excepted_parts_to_move = 0

        # When
        fund.add_stock(stock_aapl)

        # Then
        assert stock_aapl.parts_to_move == excepted_parts_to_move
