from datetime import datetime, timezone
from decimal import Decimal
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, ForeignKey, Index, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from shared.db.config import Base

if TYPE_CHECKING:
    from shared.db.models.asset import AssetTable


class AssetTransactionTable(Base):
    """
    Tracks individual transactions (purchases, sales) for assets.
    Used to calculate weighted average purchase price (PRUM) and maintain transaction history.
    """

    __tablename__ = "asset_transactions"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    asset_id: Mapped[int] = mapped_column(
        ForeignKey("stocks.id", ondelete="CASCADE"), nullable=False
    )

    transaction_type: Mapped[str] = mapped_column(String(20), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(20, 10), nullable=False)
    price: Mapped[Decimal] = mapped_column(Numeric(20, 10), nullable=False)
    total_cost: Mapped[Decimal] = mapped_column(Numeric(20, 10), nullable=False)
    order_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    created_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    asset: Mapped["AssetTable"] = relationship(  # noqa: F821
        "AssetTable", back_populates="transactions"
    )

    __table_args__ = (Index("idx_asset_timestamp", "asset_id", "timestamp"),)
