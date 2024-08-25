from src.fund import Fund
from src.stock import Stock
from src.utils import check_and_update_config
from tests.utils import load_config


class TestUtils:
    def test_set_classes_should_well_set_classes(self):
        # Given
        actual_config_file_path = "tests/data/normal_config.json"
        actual_config = load_config(actual_config_file_path)

        # When
        fund = Fund.parse_file(actual_config_file_path)

        # Then
        assert fund.name == actual_config["fund_name"]
        assert len(fund.stocks) == len(actual_config["stocks"])
        assert fund.total_current_repartition == sum(
            [stock["current_repartition"] for stock in actual_config["stocks"]]
        )

    def test_update_fund_name_should_update_class(self, caplog):
        # Given
        actual_config_file_path = "tests/data/normal_config.json"
        actual_config = load_config(actual_config_file_path)

        fund = Fund("Test")

        # When
        actual_fund = check_and_update_config(fund, actual_config_file_path)

        # Then
        assert actual_fund.name == actual_config["fund_name"]

    def test_update_stock_repartition_should_update_class(self, caplog):
        # Given
        actual_config_file_path = "tests/data/normal_config.json"
        actual_config = load_config(actual_config_file_path)

        fund = Fund(
            "tata",
            [
                Stock(
                    "on",
                    1,
                    107.37,
                    50,
                    50,
                    10,
                    15,
                ),
                Stock(
                    "AAPL",
                    1,
                    107.37,
                    50,
                    50,
                    10,
                    15,
                ),
            ],
        )

        # When
        actual_fund = check_and_update_config(fund, actual_config_file_path)

        # Then
        assert (
            actual_fund.get_stock_from_symbol("on").current_repartition
            == actual_config["stocks"][1]["current_repartition"]
        )
        assert actual_fund.total_current_repartition == sum(
            [stock.current_repartition for stock in actual_fund.stocks]
        )
        assert actual_fund.check_on_repartition(actual_fund.total_current_repartition)

    def test_check_and_update_config_with_same_config_should_return_same(self, caplog):
        # Given
        actual_config_file_path = "tests/data/normal_config.json"
        actual_config = load_config(actual_config_file_path)

        excepted_fund = Fund.parse_obj(actual_config)

        # When
        actual_fund = check_and_update_config(excepted_fund, actual_config_file_path)

        # Then
        assert actual_fund == excepted_fund

    def test_add_stock_should_well_redefine_amount_to_move(self, mocker):
        # Given
        actual_config_file_path = "tests/data/normal_config.json"
        actual_config = load_config(actual_config_file_path)
        current_fund = Fund.parse_obj(actual_config)
        new_config_file_path = "tests/data/three_stocks_config.json"

        expected_amount_to_move_for_aapl = current_fund.define_amount_to_move(
            current_fund.get_stock_from_symbol("AAPL")
        )

        # Then
        assert (
            current_fund.get_stock_from_symbol("AAPL").amount_to_move
            == expected_amount_to_move_for_aapl
        )

        # When
        updated_fund = check_and_update_config(current_fund, new_config_file_path)
        expected_amount_to_move_for_aapl_after_add_googl = (
            updated_fund.define_amount_to_move(
                updated_fund.get_stock_from_symbol("AAPL")
            )
        )
        expected_amount_to_move_for_googl = updated_fund.define_amount_to_move(
            updated_fund.get_stock_from_symbol("GOOGL")
        )

        actual_amount_to_move_for_aapl = updated_fund.get_stock_from_symbol(
            "AAPL"
        ).amount_to_move
        actual_amount_to_move_for_googl = updated_fund.get_stock_from_symbol(
            "GOOGL"
        ).amount_to_move

        # Then
        assert actual_amount_to_move_for_aapl != expected_amount_to_move_for_aapl
        assert (
            actual_amount_to_move_for_aapl
            == expected_amount_to_move_for_aapl_after_add_googl
        )
        assert (
            actual_amount_to_move_for_aapl
            == expected_amount_to_move_for_aapl_after_add_googl
        )
        assert actual_amount_to_move_for_googl == expected_amount_to_move_for_googl
