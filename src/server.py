import os
import sys
from logging import Logger, getLogger
from pathlib import Path
from time import sleep

from dotenv import load_dotenv

load_dotenv()

sys.path.append(Path(__file__).parent.absolute().as_posix())

from fund import Fund
from logger import setup_logging
from utils import check_and_update_config


class Server:
    def __init__(self, logger: Logger, config_file_path: str, sleep_time: int):
        self._stop = False
        self.logger = logger
        self.config_file_path = config_file_path
        self.sleep_time = sleep_time
        self.fund = None

    def stop(self):
        self._stop = True

    def define_fund(self):
        is_parsed = False
        while not is_parsed and not self._stop:
            try:
                self.fund = Fund.parse_file(self.config_file_path)
                is_parsed = True
            except Exception as ex:
                self.logger.error(ex)
            finally:
                sleep(self.sleep_time)

    def define_server(self):
        # define the server
        while not self._stop:
            try:
                self.fund = check_and_update_config(self.fund, self.config_file_path)
            except Exception as ex:
                self.logger.error(ex)
            finally:
                sleep(self.sleep_time)


if __name__ == "__main__":  # pragma: no cover
    setup_logging()
    logger = getLogger(__name__)

    logger.info("Starting the application")

    # get config file path to environment variable
    config_file_path = os.getenv("CONFIG_FILE_PATH", "config.json")

    # get sleep time from environment variable
    sleep_time = int(os.getenv("FUND_UPDATE_INTERVAL", 30))

    server = Server(logger, config_file_path, sleep_time)
    server.define_fund()
    server.define_server()
