import logging
import os
import sys
import time
from pathlib import Path

sys.path.append(Path(__file__).parent.absolute().as_posix())

from fund import Fund
from logger import setup_logging
from utils import check_and_update_config


def define_server():
    setup_logging()
    logger = logging.getLogger(__name__)
    logger.info("Starting the application")

    # get config file path to environment variable
    config_file_path = os.getenv("CONFIG_FILE_PATH", "config.json")

    fund = Fund.parse_file(config_file_path)

    # define the server
    while True:
        logger.info("Check if alert has to be send")
        fund = check_and_update_config(fund, config_file_path)

        # get sleep time from environment variable
        sleep_time = int(os.getenv("FUND_UPDATE_INTERVAL", 30))
        time.sleep(sleep_time)


if __name__ == "__main__":
    define_server()
