from loguru import logger

from src.old.stock import Stock
from src.services.fund import FundService
from src.services.stock import StockService

if __name__ == "__main__":
    funds = FundService.get_all()
    for fund in funds:
        logger.info(f"Fund: {fund.fund_name}")
        for stock in fund.stocks:
            logger.info(
                f"  Stock: {stock.symbol}, Shares: {stock.shares_number}, Price: {stock.today_price}, Name: {stock.name}"
            )
            if stock.name == "NULL":
                stock.name = Stock.get_long_name(stock.symbol)
                StockService.update(fund.id, stock.id, stock)
                logger.info(f"    Updated name to: {stock.name}")
