from src.models.pydantic.schema import (
    FundSchema,
    StockSchema,
)
from src.models.sqlalchemy.fund import FundTable


def fund_table_to_pydantic(fund: FundTable) -> FundSchema:
    """Convert database Fund model to Pydantic model"""
    return FundSchema(
        id=str(fund.id),
        fund_name=fund.name,
        stocks=[
            StockSchema(
                id=str(stock.id),
                symbol=stock.symbol,
                parts_number=stock.parts_number,
                prum=stock.prum,
                current_repartition=stock.current_repartition,
                target_repartition=stock.target_repartition,
                arbitration_threshold=stock.arbitration_threshold,
                threshold_to_alert=stock.threshold_to_alert,
            )
            for stock in fund.stocks
        ],
        created_at=fund.created_at,
        updated_at=fund.updated_at,
    )
