from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from shared.db.config import SessionLocal
from shared.db.models.asset import AssetTable
from shared.db.models.transaction import AssetTransactionTable
from src.models.pydantic.schema import TransactionSchema


class TransactionService:
    """Service for asset transaction business logic"""

    @staticmethod
    def get_all(
        fund_id: Optional[int] = None,
        asset_id: Optional[int] = None,
        limit: int = 100,
    ) -> List[TransactionSchema]:
        """Get all transactions with optional filters"""
        with SessionLocal() as session:
            stmt = (
                select(AssetTransactionTable)
                .join(AssetTable, AssetTransactionTable.asset_id == AssetTable.id)
                .options(selectinload(AssetTransactionTable.asset))
                .order_by(AssetTransactionTable.timestamp.desc())
                .limit(limit)
            )

            if asset_id is not None:
                stmt = stmt.where(AssetTransactionTable.asset_id == asset_id)

            if fund_id is not None:
                stmt = stmt.where(AssetTable.fund_id == fund_id)

            transactions = session.scalars(stmt).all()

            return [
                TransactionSchema(
                    id=tx.id,
                    asset_id=tx.asset_id,
                    asset_symbol=tx.asset.symbol,
                    asset_name=tx.asset.name,
                    transaction_type=tx.transaction_type,
                    timestamp=tx.timestamp,
                    quantity=float(tx.quantity),
                    price=float(tx.price),
                    total_cost=float(tx.total_cost),
                    order_id=tx.order_id,
                    created_at=tx.created_at,
                )
                for tx in transactions
            ]
