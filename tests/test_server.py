import copy
import logging
import os
import queue
from logging import getLogger
from threading import Thread
from time import sleep

import pytest
from dotenv import load_dotenv

from src.server import Server

logger = logging.getLogger(__name__)

load_dotenv()


# Create a queue for the log records
log_queue = queue.Queue()


# Create a handler that puts the log records into the queue
class QueueHandler(logging.Handler):
    def __init__(self, log_queue):
        super().__init__()
        self.log_queue = log_queue

    def emit(self, record):
        self.log_queue.put(record)


@pytest.fixture
def server_setup():
    # Configure the logging module to use the queue handler
    handler = QueueHandler(log_queue)
    logging.basicConfig(handlers=[handler])
    logger = getLogger(__name__)

    # Set the config file path environment variable
    os.environ["CONFIG_FILE_PATH"] = "tests/data/server_config.json"
    config_file_path = os.getenv("CONFIG_FILE_PATH", "config.json")

    # get sleep time from environment variable
    sleep_time = int(os.getenv("FUND_UPDATE_INTERVAL", 2))

    # Launch the server
    server = Server(logger, config_file_path, sleep_time)
    server.define_fund()
    actual_fund = server.fund
    update_fund = copy.deepcopy(actual_fund)

    server_thread = Thread(target=server.define_server)
    server_thread.start()

    yield server, update_fund

    # Teardown - stop the server, join the server thread and rollback the config file
    server.stop()
    server_thread.join()
    actual_fund.write_to_file(config_file_path)


def test_server(server_setup, caplog):
    # Given
    server, update_fund = server_setup

    # When
    update_fund.stocks[0].prum = 10
    update_fund.write_to_file(server.config_file_path)

    # wait for server to update the fund
    sleep(server.sleep_time)

    # Then
    while not log_queue.empty():
        record = log_queue.get()
        print(record.message)

    assert server.fund, update_fund
    assert server.fund.stocks[0].prum, update_fund.stocks[0].prum
    # assert server.fund.stocks[0].symbol, update_fund.stocks[0].symbol
