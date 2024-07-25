import json
import logging

from src.fund import Fund
from src.stock import Stock

logger = logging.getLogger(__name__)


# Function to load configuration from the JSON file
def load_config(file_path: str) -> dict:
    with open(file_path, "r") as file:
        return json.load(file)


def set_classes(config: dict) -> Fund:
    stocks = []
    for stock in config["stocks"]:
        stocks.append(
            Stock(
                stock["symbol"],
                stock["parts_number"],
                stock["prum"],
                stock["current_repartition"],
                stock["target_repartition"],
                stock["arbitration_threshold"],
                stock["threshold_to_alert"],
            )
        )
    fund = Fund(config["fund_name"], stocks)

    return fund


# Function to check the JSON file and update classes
def check_and_update_config(fund: Fund, file_path: str)-> Fund:
    # Fetch current configuration
    logging.info("Checking if configuration variables changed")
    current_env_vars = load_config(file_path)
    current_fund = set_classes(current_env_vars)

    # Check for fund name change and update class
    fund_name_key = "fund_name"
    current_fund_name = current_fund.name
    if current_fund_name != fund.name:
        logging.info(
            f"Detected change in {fund_name_key}: {fund.name} -> {current_fund_name}"
        )

    # Check for stock repartition change and update class
    for stock in fund.stocks:
        for current_stock in current_env_vars["stocks"]:
            if stock.symbol != current_stock["symbol"]:
                continue
            else:
                current_repartition = current_stock["current_repartition"]
                if stock.current_repartition != current_repartition:
                    logging.info(
                        f"Detected change in current repartition: {stock.current_repartition} -> {current_repartition}"
                    )
    return current_fund
