from sqlalchemy import delete, select, update
from sqlalchemy.orm import selectinload

from shared.db.config import SessionLocal
from shared.db.models.asset import AssetTable as StockTable
from shared.db.models.fund import FundTable
from src.models.pydantic.schema import StockSchema


class StockRepository:
    @staticmethod
    def add(fund_id: str, stock: StockSchema) -> FundTable | None:
        """Add a stock to a fund"""
        with SessionLocal() as session:
            with session.begin():
                # Exclude id field from stock data
                stock_data = stock.model_dump(
                    exclude={
                        "id",
                        "gain_loss",
                        "gain_loss_percentage",
                        "market_value",
                        "today_price",
                        "prum",
                    }
                )
                session.add(StockTable(fund_id=fund_id, **stock_data))

            # Return the fund with stocks loaded
            fund = session.scalars(
                select(FundTable)
                .options(selectinload(FundTable.stocks))
                .where(FundTable.id == fund_id)
            ).one_or_none()
        return fund

    @staticmethod
    def update(fund_id: str, stock_id: str, stock: StockSchema) -> FundTable | None:
        """Update a stock in a fund"""
        stmt = (
            update(StockTable)
            .where(
                StockTable.fund_id == fund_id,
                StockTable.id == stock_id,
            )
            .values(
                **stock.model_dump(
                    exclude={
                        "id",
                        "gain_loss",
                        "gain_loss_percentage",
                        "market_value",
                        "today_price",
                        "prum",
                    }
                )
            )
        )
        with SessionLocal() as session:
            with session.begin():
                result = session.execute(stmt)
                if result.rowcount == 0:
                    return None

            # Return the fund with stocks loaded
            fund = session.scalars(
                select(FundTable)
                .options(selectinload(FundTable.stocks))
                .where(FundTable.id == fund_id)
            ).one_or_none()
        return fund

    @staticmethod
    def remove(fund_id: str, stock_id: str) -> FundTable | None:
        """Remove a stock from a fund"""
        stmt = delete(StockTable).where(
            StockTable.fund_id == fund_id, StockTable.id == stock_id
        )
        with SessionLocal() as session:
            with session.begin():
                result = session.execute(stmt)
                if result.rowcount == 0:
                    return None

            # Return the fund with stocks loaded
            fund = session.scalars(
                select(FundTable)
                .options(selectinload(FundTable.stocks))
                .where(FundTable.id == fund_id)
            ).one_or_none()
        return fund
