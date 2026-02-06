from typing import List

from sqlalchemy import delete, select, update
from sqlalchemy.orm import selectinload

from shared.db.config import SessionLocal, with_db_retry
from shared.db.models.fund import FundTable


class FundRepository:
    @staticmethod
    @with_db_retry(max_retries=3)
    def get_all() -> List[FundTable]:
        """Get all funds with their assets (stocks)"""
        with SessionLocal() as session:
            stmt = (
                select(FundTable)
                .options(selectinload(FundTable.assets))
                .order_by(FundTable.created_at.desc())
            )
            records = session.scalars(stmt).all()
        return records

    @staticmethod
    @with_db_retry(max_retries=3)
    def get_by_id(id: str) -> FundTable | None:
        """Get a fund by ID with its assets (stocks)"""
        with SessionLocal() as session:
            stmt = (
                select(FundTable)
                .options(selectinload(FundTable.assets))
                .where(FundTable.id == id)
            )
            record = session.scalars(stmt).one_or_none()
        return record

    @staticmethod
    @with_db_retry(max_retries=3)
    def create(fund_name: str) -> FundTable:
        """Create a new fund"""
        with SessionLocal() as session:
            with session.begin():
                fund_table = FundTable(name=fund_name)
                session.add(fund_table)
                session.flush()

            # Fetch the fund with assets loaded before session closes
            fund_with_assets = session.scalars(
                select(FundTable)
                .options(selectinload(FundTable.assets))
                .where(FundTable.id == fund_table.id)
            ).one()

        return fund_with_assets

    @staticmethod
    @with_db_retry(max_retries=3)
    def update(fund_id: str, name: str | None = None) -> FundTable | None:
        """Update fund details"""
        stmt = update(FundTable).where(FundTable.id == fund_id).values(name=name)
        with SessionLocal() as session:
            with session.begin():
                result = session.execute(stmt)
                if result.rowcount == 0:
                    return None

            # Fetch and return the updated fund with assets
            fund = session.scalars(
                select(FundTable)
                .options(selectinload(FundTable.assets))
                .where(FundTable.id == fund_id)
            ).one_or_none()
        return fund

    @staticmethod
    @with_db_retry(max_retries=3)
    def delete(fund_id: str) -> bool:
        """Delete a fund (cascade deletes assets/stocks)"""
        stmt = delete(FundTable).where(FundTable.id == fund_id)
        with SessionLocal() as session:
            with session.begin():
                session.execute(stmt)
        return True
