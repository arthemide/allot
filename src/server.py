import os
import sys
from logging import getLogger
from pathlib import Path
from time import sleep

from dotenv import load_dotenv

load_dotenv()

sys.path.append(Path(__file__).parent.absolute().as_posix())

from fund import Fund
from logger import setup_logging
from utils import check_and_update_config


def define_server():
    setup_logging()
    logger = getLogger(__name__)
    logger.info("Starting the application")

    # get config file path to environment variable
    config_file_path = os.getenv("CONFIG_FILE_PATH", "config.json")

    # get sleep time from environment variable
    sleep_time = int(os.getenv("FUND_UPDATE_INTERVAL", 30))

    is_parsed = False
    fund = None
    while not is_parsed:
        try:
            fund = Fund.parse_file(config_file_path)
            is_parsed = True
        except Exception as ex:
            logger.error(ex)
        finally:
            sleep(sleep_time)

    # define the server
    while True:
        logger.info("Check if alert has to be send")

        try:
            fund = check_and_update_config(fund, config_file_path)
        except Exception as ex:
            logger.error(ex)
        finally:
            sleep(sleep_time)


if __name__ == "__main__":
    define_server()
