import logging

from src.fund import Fund

logger = logging.getLogger(__name__)


# Function to check the JSON file and update classes
def check_and_update_config(cur_fund: Fund, file_path: str) -> Fund:
    # Fetch current configuration
    logging.info("Checking if configuration variables changed")
    new_fund = Fund.parse_file(file_path)

    # Check for fund name change and update class
    if new_fund.name != cur_fund.name:
        logging.warn(
            f"Detected change in fund_name: {cur_fund.name} -> {new_fund.name}"
        )
        return new_fund

    # Check for stock repartition change and update class
    if new_fund.stocks != cur_fund.stocks:
        logging.info("Detected change in stock repartition")
        return new_fund
    return cur_fund
