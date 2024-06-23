from src.fund import Fund
from src.stock import Stock
from src.utils import check_and_update_config, load_config


class TestUtils:
    def test_update_fund_name_should_update_class(self, caplog):
        # Given
        actual_config_file_path = "tests/data/normal_config.json"
        actual_config = load_config(actual_config_file_path)

        fund = Fund("Test")

        # When
        check_and_update_config(fund, actual_config_file_path)

        # Then
        assert fund.name == actual_config["fund_name"]

    def test_update_stock_repartition_should_update_class(self, caplog):
        # Given
        actual_config_file_path = "tests/data/normal_config.json"
        actual_config = load_config(actual_config_file_path)
        excepted_repartition = 75.0

        fund = Fund("tata", [Stock("on", 2, 1.2, 50), Stock("AAPL", 2, 2, 50)])

        # When
        check_and_update_config(fund, actual_config_file_path)

        # Then
        assert (
            fund.get_stock_from_symbol("on").repartition
            == actual_config["stocks"][1]["repartition"]
        )
