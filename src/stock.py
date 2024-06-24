import logging

import yfinance as yf

from src.logger import setup_logging

logger = logging.getLogger(__name__)


class Stock:
    def __init__(
        self,
        symbol: str,
        parts_number: int = 1,
        prum: float = 0.0,
        repartition: float = 100.0,
    ):
        """
        Initializes a Stock object.

        Args:
            symbol (str): The symbol of the stock.
            current_price (float): The current price of the stock.
            parts_number (int, optional): The number of parts of the stock. Defaults to 1.
            prum (float, optional): The "Prix de Revient Unitaire Moyen" value. Defaults to 0.0.
            current_amount (float): The current amount of the stock.
            current_profit (float): The current profit of the stock.
            repartition (float): The repartition in percentage on the fund of the stock.
        """
        self.symbol = symbol
        self.current_price = self.get_stock_price(symbol)

        self.parts_number = parts_number
        self.prum = prum

        self.current_amount = round(self.parts_number * self.current_price, 2)
        self.current_profit = round(
            (self.current_price - self.prum) * self.parts_number, 2
        )

        self.check_repartition(repartition)
        self.repartition = repartition

    # make sure repartition is between 0 and 100
    def check_repartition(self, repartition: float):
        if repartition < 0 or repartition > 100:
            raise ValueError("The repartition must be between 0 and 100")
        return True

    # get a stock price from yahoo finance
    def get_stock_price(self, symbol: str, period: str = "1d") -> float:
        stock_data = yf.Ticker(symbol)
        stock_history = stock_data.history(period=period)
        if stock_history.empty:
            raise UserWarning(f"{symbol}: No data found, symbol may be delisted")

        current_price = stock_history["Close"].iloc[0]
        logger.info(f"Current price of {symbol} on period {period} is {current_price}")
        return current_price

    # get the stock price evolution percentage
    # TODO: implement the method
    # def get_stock_price_evolution_percentage(self):
    #     pass

if __name__ == "__main__":  # pragma: no cover
    setup_logging()
    logger.info("Starting the stock script")
    stock = Stock("APDL")
    logger.info(stock.current_price)
    logger.info("Ending the stock script")
