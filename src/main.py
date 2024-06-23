import logging
import time

from logger import setup_logging
from utils import check_and_update_config, load_config, set_classes

# def send_alert():


# Main function
def main():
    setup_logging()
    logger = logging.getLogger(__name__)
    logger.info("Starting the application")

    config_file_path = "config.json"
    config = load_config(config_file_path)

    fund = set_classes(config)

    while True:
        logger.info("Check if alert has to be send")
        check_and_update_config(fund, config_file_path)
        # Sleep for some time before checking again
        time.sleep(10)


if __name__ == "__main__":
    main()
