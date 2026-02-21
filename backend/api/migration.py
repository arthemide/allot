from loguru import logger

from src.services.fund import FundService
from src.services.stock import StockService
from src.services.yfinance_utils import get_long_name

if __name__ == "__main__":
    funds = FundService.get_all()
    for fund in funds:
        logger.info(f"Fund: {fund.fund_name}")
        for asset in fund.assets:
            logger.info(
                f"  Stock: {asset.symbol}, Shares: {asset.shares_number}, Price: {asset.today_price}, Name: {asset.name}"
            )
            if asset.name == "NULL":
                asset.name = get_long_name(asset.symbol)
                StockService.update(fund.id, asset.id, asset)
                logger.info(f"    Updated name to: {asset.name}")
