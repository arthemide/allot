import json
from logging import Handler, Logger, basicConfig, getLogger
from queue import Queue

from api.tests.server import Server
from loguru import logger

from src.old.fund import Fund

# Default sleep time for tests
SLEEP_TIME = 5

log_queue = Queue()


# Create a handler that puts the log records into the queue
class QueueHandler(Handler):
    def __init__(self, log_queue):
        super().__init__()
        self.log_queue = log_queue

    def emit(self, record):
        self.log_queue.put(record)


def setup_logging() -> tuple[Logger, Queue]:
    # Configure the logging module to use the queue handler
    handler = QueueHandler(log_queue)
    basicConfig(handlers=[handler])
    logger = getLogger(__name__)

    return logger, log_queue


def setup_server(logger: Logger, config_file_path: str) -> Server:
    # Launch the server
    return Server(logger, config_file_path, SLEEP_TIME)


# Function to load configuration from the JSON file
def load_config(file_path: str) -> dict:
    with open(file_path, "r") as file:
        return json.load(file)


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
