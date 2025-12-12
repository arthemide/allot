import os

from dotenv import load_dotenv

load_dotenv()


# get config file path to environment variable
CONFIG_FILE_PATH = os.getenv("CONFIG_FILE_PATH", "config.json")

# get sleep time from environment variable
SLEEP_TIME = int(os.getenv("FUND_UPDATE_INTERVAL", 30))
