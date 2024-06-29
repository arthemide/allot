from src.fund import Fund
from src.stock import Stock
from src.utils import check_and_update_config, load_config, set_classes


class TestUtils:
    def test_set_classes_should_well_set_classes(self):
        # Given
        actual_config_file_path = "tests/data/normal_config.json"
        actual_config = load_config(actual_config_file_path)

        # When
        fund = set_classes(actual_config)

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
