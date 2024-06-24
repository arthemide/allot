import logging
from typing import List, Optional

from src.stock import Stock

logger = logging.getLogger(__name__)


class Fund:
    def __init__(self, name: str, stocks: Optional[List[Stock]] = None):
        self.name = name
        if stocks is None:
            self.stocks = []
        else:
            self.stocks = stocks
        self.total_amount = self.define_total_amount()
        self.total_repartition = self.define_total_repartition()

    def define_total_amount(self):
        if len(self.stocks) == 0:
            return 0.0
        else:
            return sum([stock.current_amount for stock in self.stocks])

    def check_on_repartition(self, repartition: float):
        if repartition > 100:
            raise ValueError(
                f"The repartition of the fund is greater than 100% ({repartition})."
                "Please adjust the repartition of the stocks."
            )
        elif repartition < 100:
            logging.warning(
                f"The repartition of the fund is lower than 100% ({repartition})."
                "Please adjust the repartition of the stocks."
            )
        return True

    def define_total_repartition(self):
        if len(self.stocks) == 0:
            return 0.0
        else:
            total_repartition = sum([stock.repartition for stock in self.stocks])
            if self.check_on_repartition(total_repartition):
                return total_repartition

    def add_stock(self, stock: Stock):
        # check if the stock is already in the fund
        for s in self.stocks:
            if s.symbol == stock.symbol:
                raise ValueError(f"{stock.symbol} is already in the fund")

        # check if the stock repartition is not greater than 100%
        total_repartition = (
            sum([s.repartition for s in self.stocks]) + stock.repartition
        )
        if self.check_on_repartition(total_repartition):
            self.total_repartition = total_repartition

        self.total_amount += stock.current_amount

        self.stocks.append(stock)

    def remove_stock(self, stock: Stock):
        if stock not in self.stocks:
            raise ValueError(f"{stock.symbol} is not in the fund")

        self.total_amount -= stock.current_amount

        self.stocks.remove(stock)

    def update_repartition(self, stock: Stock, new_repartition: float):
        if stock not in self.stocks:
            raise ValueError(f"{stock.symbol} is not in the fund")

        # check if the stock repartition is not greater than 100%
        total_repartition = (
            sum([s.repartition for s in self.stocks])
            - stock.repartition
            + new_repartition
        )
        if self.check_on_repartition(total_repartition):
            self.total_repartition = total_repartition

        stock.repartition = new_repartition

    def get_stock_from_symbol(self, symbol: str) -> Stock:
        for stock in self.stocks:
            if stock.symbol == symbol:
                return stock
        raise ValueError(f"{symbol} is not in the fund")


if __name__ == "__main__":  # pragma: no cover
    fund = Fund("My Fund")
    stock = Stock("AAPL", 1, 107.37)
    fund.add_stock(stock)
    logger.info(fund.stocks)
    logger.info(fund.get_stock_from_symbol("AAPL"))
    fund.remove_stock(stock)
    logger.info(fund.stocks)
    logger.info(fund.get_stock_from_symbol("AAPL"))
