from shared.db.models.asset import AssetTable
from shared.db.models.fund import FundTable
from src.models.pydantic.schema import (
    FundSchema,
    StockSchema,
)
from src.services.yfinance_utils import get_stock_price


def _compute_from_transactions(stock: AssetTable) -> tuple[float, float] | None:
    """
    Compute (cost, shares_number) from transaction history when available.
    Returns None if the asset has no transactions.
    """
    transactions = getattr(stock, "transactions", None)
    if not transactions:
        return None

    base_qty = float(stock.shares_number) if stock.shares_number else 0.0
    base_cost = (
        base_qty * float(stock.base_prum) if stock.base_prum and base_qty > 0 else 0.0
    )

    total_qty = base_qty
    total_cost = base_cost

    for tx in transactions:
        qty = float(tx.quantity)
        cost = float(tx.total_cost)
        if tx.transaction_type == "buy":
            total_qty += qty
            total_cost += cost
        elif tx.transaction_type == "sell":
            total_qty -= qty
            total_cost -= cost

    return total_cost, total_qty


def fund_table_to_pydantic(fund: FundTable) -> FundSchema:
    """Convert database Fund model to Pydantic model"""
    assets = []
    total_cost = 0.0
    total_market_value = 0.0
    total_gain_loss = 0.0
    total_gain_loss_percentage = 0.0

    for asset in fund.assets:
        tx_values = _compute_from_transactions(asset)
        if tx_values is not None:
            cost, shares_number = tx_values
        else:
            cost = asset.cost
            shares_number = asset.shares_number

        prum = cost / shares_number if shares_number else 0.0
        today_price = get_stock_price(asset.symbol)
        market_value = 0.0
        gain_loss = 0.0
        gain_loss_percentage = 0.0
        if today_price:
            market_value = shares_number * today_price
            gain_loss = round((market_value - cost), 2)
            gain_loss_percentage = (
                round((gain_loss * 100) / cost, 2) if cost != 0 else 0.0
            )

        # Accumulate totals
        total_cost += cost
        total_market_value += market_value
        total_gain_loss += gain_loss
        total_gain_loss_percentage += gain_loss_percentage

        assets.append(
            StockSchema(
                id=str(asset.id),
                name=asset.name,
                symbol=asset.symbol,
                shares_number=shares_number,
                cost=cost,
                prum=prum,
                today_price=today_price,
                market_value=market_value,
                gain_loss=gain_loss,
                gain_loss_percentage=gain_loss_percentage,
                current_repartition=asset.current_repartition,
                target_repartition=asset.target_repartition,
                arbitration_threshold=asset.arbitration_threshold,
                threshold_to_alert=asset.threshold_to_alert,
            )
        )

    # Calculate average gain/loss percentage
    average_gain_loss_percentage = 0.0
    if len(assets) > 0 and total_cost > 0:
        average_gain_loss_percentage = round(
            total_gain_loss_percentage / len(assets), 2
        )

    return FundSchema(
        id=str(fund.id),
        fund_name=fund.name,
        stocks=assets,
        created_at=fund.created_at,
        updated_at=fund.updated_at,
        total_cost=round(total_cost, 2),
        total_market_value=round(total_market_value, 2),
        total_gain_loss=round(total_gain_loss, 2),
        average_gain_loss_percentage=average_gain_loss_percentage,
    )
