from loguru import logger

from src.services.fund import FundService
from src.services.stock import StockService
from src.services.yfinance_utils import get_long_name

if __name__ == "__main__":
    funds = FundService.get_all()
    for fund in funds:
        logger.info(f"Fund: {fund.fund_name}")
        for stock in fund.stocks:
            logger.info(
                f"  Stock: {stock.symbol}, Shares: {stock.shares_number}, Price: {stock.today_price}, Name: {stock.name}"
            )
            if stock.name == "NULL":
                stock.name = get_long_name(stock.symbol)
                StockService.update(fund.id, stock.id, stock)
                logger.info(f"    Updated name to: {stock.name}")
