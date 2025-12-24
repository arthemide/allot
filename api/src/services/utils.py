from src.models.pydantic.schema import (
    FundSchema,
    StockSchema,
)
from src.models.sqlalchemy.fund import FundTable
from src.old.stock import Stock


def fund_table_to_pydantic(fund: FundTable) -> FundSchema:
    """Convert database Fund model to Pydantic model"""
    stocks = []
    total_cost = 0.0
    total_market_value = 0.0
    total_gain_loss = 0.0
    total_gain_loss_percentage = 0.0

    for stock in fund.stocks:
        cost = stock.cost
        prum = stock.cost / stock.shares_number
        today_price = Stock.get_stock_price(stock.symbol)
        market_value = 0.0
        gain_loss = 0.0
        gain_loss_percentage = 0.0
        if today_price:
            market_value = stock.shares_number * today_price
            gain_loss = round((market_value - cost), 2)
            gain_loss_percentage = (
                round((gain_loss * 100) / market_value, 2) if cost != 0 else 0.0
            )

        # Accumulate totals
        total_cost += cost
        total_market_value += market_value
        total_gain_loss += gain_loss
        total_gain_loss_percentage += gain_loss_percentage

        stocks.append(
            StockSchema(
                id=str(stock.id),
                name=stock.name,
                symbol=stock.symbol,
                shares_number=stock.shares_number,
                cost=cost,
                prum=prum,
                today_price=today_price,
                market_value=market_value,
                gain_loss=gain_loss,
                gain_loss_percentage=gain_loss_percentage,
                current_repartition=stock.current_repartition,
                target_repartition=stock.target_repartition,
                arbitration_threshold=stock.arbitration_threshold,
                threshold_to_alert=stock.threshold_to_alert,
            )
        )

    # Calculate average gain/loss percentage
    average_gain_loss_percentage = 0.0
    if len(stocks) > 0 and total_cost > 0:
        average_gain_loss_percentage = round(
            total_gain_loss_percentage / len(stocks), 2
        )

    return FundSchema(
        id=str(fund.id),
        fund_name=fund.name,
        stocks=stocks,
        created_at=fund.created_at,
        updated_at=fund.updated_at,
        total_cost=round(total_cost, 2),
        total_market_value=round(total_market_value, 2),
        total_gain_loss=round(total_gain_loss, 2),
        average_gain_loss_percentage=average_gain_loss_percentage,
    )
