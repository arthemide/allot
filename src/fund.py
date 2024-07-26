import logging
from typing import List, Optional

from src.stock import Stock

logger = logging.getLogger(__name__)


class Fund:
    def __init__(self, name: str, stocks: Optional[List[Stock]] = None):
        self.name = name
        self.stocks = []
        self.total_amount = 0.0
        self.total_current_repartition = 0.0
        self.total_target_repartition = 0.0
        if stocks:
            self.add_stocks(stocks)

    def check_on_repartition(self, repartition: float) -> bool:
        if repartition != 100:
            raise ValueError(
                f"The repartition of the fund is not equal to 100% ({repartition})."
                "Please adjust the repartition of the stocks."
            )
        return True

    def update_total_repartition(
        self,
        attr_as_str: str,
        current_repartition: float = 0.0,
        stocks: list[Stock] = [],
    ) -> float:
        total_repartition = (
            sum([getattr(stock, attr_as_str) for stock in self.stocks])
            + sum([getattr(stock, attr_as_str) for stock in stocks])
            + current_repartition
        )
        try:
            self.check_on_repartition(total_repartition)
        except ValueError as e:
            raise e
        return total_repartition

    def define_amount_to_move(self, stock: Stock) -> float:
        return round(
            (stock.target_repartition - stock.current_repartition)
            / 100
            * self.total_amount,
            2,
        )

    def check_stock_not_existing(self, stock) -> bool:
        if self.stocks == []:
            return True
        for s in self.stocks:
            if s.symbol == stock.symbol:
                raise ValueError(f"{stock.symbol} is already in the fund")
        return True

    def add_stock(self, stock: Stock):
        # check if the stock is already in the fund
        self.check_stock_not_existing(stock)

        # check if the current stock repartition is not greater than 100%
        self.total_current_repartition = self.update_total_repartition(
            "current_repartition", stock.current_repartition
        )

        # check if the target stock repartition is not greater than 100%
        self.total_target_repartition = self.update_total_repartition(
            "target_repartition", stock.target_repartition
        )

        # update the total amount of the fund
        self.total_amount += stock.current_amount

        # define the amount to move for the stock
        stock.amount_to_move = self.define_amount_to_move(stock)

        # define the parts to move for the stock
        stock.parts_to_move = stock.define_parts_to_move()

        # add the stock to the fund
        self.stocks.append(stock)

    def add_stocks(self, stocks: List[Stock]):
        # check if the stock is already in the fund
        for s in stocks:
            self.check_stock_not_existing(s)

        # check if the current stock repartition is not greater than 100%
        self.total_current_repartition = self.update_total_repartition(
            "current_repartition", 0, stocks
        )

        # check if the target stock repartition is not greater than 100%
        self.total_target_repartition = self.update_total_repartition(
            "target_repartition", 0, stocks
        )

        # update the total amount of the fund
        self.total_amount += sum([stock.current_amount for stock in stocks])

        for stock in stocks:
            # define the amount to move for the stock
            stock.amount_to_move = self.define_amount_to_move(stock)

            # define the parts to move for the stock
            stock.parts_to_move = stock.define_parts_to_move()

        # add the stock to the fund
        self.stocks.extend(stocks)

    def remove_stock(self, stock: Stock):
        if stock not in self.stocks:
            raise ValueError(f"{stock.symbol} is not in the fund")

        self.total_amount -= stock.current_amount

        self.stocks.remove(stock)

    def get_stock_from_symbol(self, symbol: str) -> Stock:
        for stock in self.stocks:
            if stock.symbol == symbol:
                return stock
        raise ValueError(f"{symbol} is not in the fund")


if __name__ == "__main__":  # pragma: no cover
    fund = Fund("My Fund")
    stock = Stock("AAPL", 107.37, 10, 15, 100, 100, 1)
    fund.add_stock(stock)
    logger.info(fund.stocks)
    logger.info(fund.get_stock_from_symbol("AAPL"))
    fund.remove_stock(stock)
    logger.info(fund.stocks)
    logger.info(fund.get_stock_from_symbol("AAPL"))
