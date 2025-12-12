from typing import Optional

import yfinance as yf
from loguru import logger

from src.logger import setup_logging
from src.models import StockConfig


class Stock:
    def __init__(
        self,
        symbol: str,
        parts_number: float,
        prum: float,
        current_repartition: float,
        target_repartition: float,
        arbitration_threshold: float,
        threshold_to_alert: float,
        amount_to_move: Optional[float] = None,
        parts_to_move: Optional[float] = None,
    ):
        """
        Initializes a Stock object.

        Args:
            symbol (str): The symbol of the stock.
            arbitration_threshold: (float): Last arbitration threshold triggered on the stock.
            current_price (float): The current price of the stock.
            parts_number (float, optional): The number of parts of the stock. Defaults to 1.
            prum (float, optional): The "Prix de Revient Unitaire Moyen" value.
            current_amount (float): The current amount of the stock.
            current_profit (float): The current profit of the stock.
            current_repartition (float): The current_repartition in percentage on the fund of the stock.
            target_repartition (float): The target_repartition in percentage on the fund of the stock.
            arbitration_threshold (float): The arbitration threshold of the stock.
            threshold_to_alert (float): The threshold define manually to alert on the stock.
            amount_to_move (float): The amount of money to move to reach the target_repartition.
            parts_to_move (float): The number of parts to move to reach the target_repartition.
        """
        self.symbol = symbol
        self.current_price = self.get_stock_price(symbol)

        self.parts_number = parts_number
        self.prum = prum

        self.current_amount = round(self.parts_number * self.current_price, 2)
        self.current_profit = round(
            (self.current_price - self.prum) * self.parts_number, 2
        )

        self.check_repartition(current_repartition)
        self.current_repartition = current_repartition

        self.check_repartition(target_repartition)
        self.target_repartition = target_repartition

        self.arbitration_threshold = arbitration_threshold

        self.threshold_to_alert = threshold_to_alert
        self.amount_to_move = amount_to_move
        self.parts_to_move = parts_to_move

    def __eq__(self, other) -> bool:
        if isinstance(other, Stock):
            return all(
                (
                    self.symbol == other.symbol,
                    self.parts_number == other.parts_number,
                    self.prum == other.prum,
                    self.current_repartition == other.current_repartition,
                    self.target_repartition == other.target_repartition,
                    self.arbitration_threshold == other.arbitration_threshold,
                    self.threshold_to_alert == other.threshold_to_alert,
                )
            )
        return NotImplemented

    # make sure repartition is between 0 and 100
    def check_repartition(self, repartition: float) -> bool:
        logger.debug("Checking repartition")
        if repartition < 0 or repartition > 100:
            raise ValueError("The repartition must be between 0 and 100")
        return True

    # get a stock price from yahoo finance
    def get_stock_price(self, symbol: str, period: str = "1d") -> float:
        logger.debug(f"Getting stock price of {symbol}")
        stock_data = yf.Ticker(symbol)
        stock_history = stock_data.history(period=period)
        if stock_history.empty:
            raise UserWarning(f"{symbol}: No data found, symbol may be delisted")

        current_price = stock_history["Close"].iloc[0]
        logger.debug(
            f"Current price of '{symbol}' on period {period} is {current_price}"
        )
        return current_price

    def define_parts_to_move(self) -> float:
        try:
            return self.amount_to_move // self.parts_number
        except ZeroDivisionError:
            return 0

    def pydantic(self):
        return StockConfig(
            symbol=self.symbol,
            parts_number=self.parts_number,
            prum=self.prum,
            current_repartition=self.current_repartition,
            target_repartition=self.target_repartition,
            arbitration_threshold=self.arbitration_threshold,
            threshold_to_alert=self.threshold_to_alert,
        )

    @staticmethod
    def search_symbol(query: str, max_results: int = 10) -> list[dict]:
        """
        Search for stock symbols using yfinance.

        Args:
            query (str): The search query (company name, symbol, etc.)
            max_results (int): Maximum number of results to return (default: 10)

        Returns:
            list[dict]: List of dictionaries containing symbol information with keys:
                - symbol: Stock ticker symbol
                - name: Company name
                - exchange: Stock exchange
                - type: Security type (e.g., EQUITY, ETF)
        """
        logger.debug(f"Searching for symbol: {query}")
        try:
            search_results = yf.Search(query)
            results = []

            for i, quote in enumerate(search_results.quotes[:max_results]):
                results.append(
                    {
                        "symbol": quote.get("symbol", ""),
                        "name": quote.get("shortname") or quote.get("longname", ""),
                        "exchange": quote.get("exchange", ""),
                        "type": quote.get("quoteType", ""),
                    }
                )

            logger.debug(f"Found {len(results)} results for query: {query}")
            return results
        except Exception as e:
            logger.error(f"Error searching for symbol '{query}': {e}")
            return []

    # get the stock price evolution percentage
    # TODO: implement the method
    # def get_stock_price_evolution_percentage(self):
    #     pass


if __name__ == "__main__":  # pragma: no cover
    setup_logging()
    logger.info("Starting the stock script")

    # Example: Search for symbols
    results = Stock.search_symbol("Afer")
    for result in results:
        print(f"{result['symbol']:15} {result['name']:50} [{result['exchange']}]")

    logger.info("Ending the stock script")
