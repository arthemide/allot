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
    fund = Fund(config["fund_name"])
    stocks = []
    for stock in config["stocks"]:
        stocks.append(
            Stock(
                stock["symbol"],
                stock["parts_number"],
                stock["prum"],
                stock["repartition"],
            )
        )

    return fund


# Function to check the JSON file and update classes
def check_and_update_config(fund: Fund, file_path: str):
    # Fetch current configuration
    logging.info("Checking if configuration variables changed")
    current_env_vars = load_config(file_path)

    # Check for changes and update classes
    fund_name_key = "fund_name"
    current_fund_name = current_env_vars[fund_name_key]
    if current_fund_name != fund.name:
        logging.info(
            f"Detected change in {fund_name_key}: {fund.name} -> {current_fund_name}"
        )
        fund.name = current_fund_name

    # for stock in current_env_vars["stocks"]:
    #     repartition_key = "repartition"
    #     current_repartition = current_env_vars[repartition_key]
    #     if current_repartition != stock.repartition:
    #         logging.info(
    #             f"Detected change in {repartition_key}: {stock.repartition} -> {current_repartition}"
    #         )
    #         if fund.check_on_repartition(current_repartition):
    #             stock.repartition = current_repartition

    # update existing stock

    # add new stock

    # check if last_update key is not now remove stock
