import copy
from threading import Thread
from time import sleep

import pytest
from dotenv import load_dotenv

from tests.utils import setup_logging, setup_server

load_dotenv()


@pytest.fixture
def server_setup():
    logger, log_queue = setup_logging()

    config_file_path = "tests/data/server_config.json"
    server = setup_server(logger, config_file_path)
    server.define_fund()
    actual_fund = server.fund
    update_fund = copy.deepcopy(actual_fund)

    server_thread = Thread(target=server.define_server)
    server_thread.start()

    yield server, update_fund, log_queue

    # Teardown - stop the server, join the server thread and rollback the config file
    server.stop()
    server_thread.join()
    actual_fund.write_to_file(config_file_path)


def test_give_fund_and_update_the_prum_should_update_the_fund(server_setup):
    # Given
    server, update_fund, log_queue = server_setup

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


def test_setting_stock_name_not_existing_should_log_error(server_setup, caplog):
    # Given
    server, update_fund, _ = server_setup

    # When
    update_fund.stocks[0].symbol = "toto"
    update_fund.write_to_file(server.config_file_path)

    # wait for server to update the fund
    sleep(server.sleep_time * 2)

    # Then
    error_expected = "toto: No data found, symbol may be delisted"
    assert error_expected in caplog.text


def test_defining_stock_not_existing_should_log_error(caplog):
    # Given
    logger, _ = setup_logging()

    config_file_path = "tests/data/stock_not_existing.json"
    server = setup_server(logger, config_file_path)

    # When
    server_thread = Thread(target=server.define_fund)
    server_thread.start()

    # Wait for a while to let the server try to parse the fund
    sleep(server.sleep_time)

    # Stop the server
    server.stop()

    server_thread.join()

    # Then
    error_expected = "toto: No data found, symbol may be delisted"
    assert error_expected in caplog.text

    # Close
    server.stop()
