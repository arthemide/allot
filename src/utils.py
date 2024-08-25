from logging import getLogger

from src.fund import Fund

logger = getLogger(__name__)


# Function to check the JSON file and update classes
def check_and_update_config(cur_fund: Fund, file_path: str) -> Fund:
    # Fetch current configuration
    logger.info("Checking if configuration variables changed")
    new_fund = Fund.parse_file(file_path)

    # Check for fund name change and update class
    if new_fund.name != cur_fund.name:
        logger.warn(f"Detected change in fund_name: {cur_fund.name} -> {new_fund.name}")
        return new_fund

    # Check for stock repartition change and update class
    if new_fund.stocks != cur_fund.stocks:
        logger.info("Detected change in stock repartition")
        return new_fund
    logger.info("No change in configuration variables")
    return cur_fund
