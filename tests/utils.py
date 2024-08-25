import json
import os
from logging import Handler, Logger, basicConfig, getLogger
from queue import Queue

from src.server import Server

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
    # Set the config file path environment variable
    os.environ["CONFIG_FILE_PATH"] = config_file_path
    config_file_path = os.getenv("CONFIG_FILE_PATH")

    # get sleep time from environment variable
    sleep_time = int(os.getenv("FUND_UPDATE_INTERVAL", 2))

    # Launch the server
    return Server(logger, config_file_path, sleep_time)


# Function to load configuration from the JSON file
def load_config(file_path: str) -> dict:
    with open(file_path, "r") as file:
        return json.load(file)
