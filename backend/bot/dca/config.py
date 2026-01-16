"""
Configuration module for Binance DCA bot.
Loads environment variables and bot parameters.
"""

import os
from typing import Optional

from dotenv import load_dotenv
from pydantic import BaseModel

# Load environment variables from .env file
load_dotenv()


class BinanceConfig(BaseModel):
    """Configuration for Binance API keys"""

    api_key: str
    api_secret: str


class DCAConfig(BaseModel):
    """Configuration for Dollar Cost Averaging"""

    # Fixed amount in USDC to invest per purchase
    amount_usdc: float

    # Trading pair (default ETH/USDC)
    symbol: str = "ETHUSDC"

    # Base currency (the one we buy)
    base_asset: str = "ETH"

    # Quote currency (the one we spend)
    quote_asset: str = "USDC"

    # Base PRUM (average purchase price) from historical purchases
    # Set this to your known average purchase price from past transactions
    # Leave None to calculate from bot purchases only
    base_prum: Optional[float] = None

    # Base quantity owned before bot started tracking
    # Used with base_prum for accurate PRUM calculation
    base_quantity: float = 0.0

    # Days of month for execution (e.g., "1,15" for 1st and 15th)
    # Format: comma-separated days (1-31) or "*" for every day
    days_of_month: str = "1,15"

    # Execution hour (24h format)
    execution_hour: int = 10

    # Execution minute
    execution_minute: int = 2


class Config:
    """Main bot configuration class"""

    def __init__(self):
        # Binance configuration
        self.binance = BinanceConfig(
            api_key=self._get_env("BINANCE_API_KEY"),
            api_secret=self._get_env("BINANCE_API_SECRET"),
        )

        # DCA configuration
        base_prum = self._get_env("DCA_BASE_PRUM")
        self.dca = DCAConfig(
            amount_usdc=float(self._get_env("DCA_AMOUNT_USDC", "30.0")),
            symbol=self._get_env("DCA_SYMBOL", "ETHUSDC"),
            base_asset=self._get_env("DCA_BASE_ASSET", "ETH"),
            quote_asset=self._get_env("DCA_QUOTE_ASSET", "USDC"),
            base_prum=float(base_prum) if base_prum else None,
            base_quantity=float(self._get_env("DCA_BASE_QUANTITY", "0.0")),
            days_of_month=self._get_env("DCA_DAYS_OF_MONTH", "1,15"),
            execution_hour=int(self._get_env("DCA_EXECUTION_HOUR", "10")),
            execution_minute=int(self._get_env("DCA_EXECUTION_MINUTE", "2")),
        )

        # Logging configuration
        self.log_level = "INFO"
        self.log_file = "logs/dca_bot.log"

        # Retry configuration
        self.max_retries = 3

        # Validate configuration
        self._validate()

    @staticmethod
    def _get_env(key: str, default: Optional[str] = None) -> str:
        """Get environment variable with error handling"""
        value = os.getenv(key, default)
        if value is None:
            raise ValueError(f"Required environment variable missing: {key}")
        return value

    def _validate(self):
        """Validate configuration"""
        if self.dca.amount_usdc <= 0:
            raise ValueError("DCA_AMOUNT_USDC must be greater than 0")

        if not (0 <= self.dca.execution_hour <= 23):
            raise ValueError("DCA_EXECUTION_HOUR must be between 0 and 23")

        if not (0 <= self.dca.execution_minute <= 59):
            raise ValueError("DCA_EXECUTION_MINUTE must be between 0 and 59")

        if not self.binance.api_key or not self.binance.api_secret:
            raise ValueError(
                "Binance API keys are required (BINANCE_API_KEY and BINANCE_API_SECRET)"
            )

    def __str__(self) -> str:
        """String representation of configuration (without secrets)"""
        schedule_info = (
            f"Days of month: {self.dca.days_of_month}"
            if self.dca.days_of_month
            else "Every day"
        )
        return f"""DCA Bot Configuration:
  Symbol: {self.dca.symbol}
  Amount: {self.dca.amount_usdc} {self.dca.quote_asset}
  Schedule: {schedule_info}
  Execution time: {self.dca.execution_hour:02d}:{self.dca.execution_minute:02d}
  Log Level: {self.log_level}
"""


# Global configuration instance (lazy-loaded)
_config: Optional[Config] = None


def get_config() -> Config:
    """Get global config instance (lazy initialization for testing)."""
    global _config
    if _config is None:
        _config = Config()
    return _config
