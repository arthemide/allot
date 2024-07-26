import logging
import os
import time

from src.logger import setup_logging
from src.utils import check_and_update_config, load_config, set_classes


def define_server():
    setup_logging()
    logger = logging.getLogger(__name__)
    logger.info("Starting the application")

    # get config file path to environment variable
    config_file_path = os.getenv("CONFIG_FILE_PATH", "config.json")

    config = load_config(config_file_path)
    fund = set_classes(config)

    # define the server
    while True:
        logger.info("Check if alert has to be send")
        fund = check_and_update_config(fund, config_file_path)

        # get sleep time from environment variable
        sleep_time = int(os.getenv("SLEEP_TIME", 2))
        time.sleep(sleep_time)
