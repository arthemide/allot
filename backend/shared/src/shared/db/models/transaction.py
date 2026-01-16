from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, Numeric, String
from sqlalchemy.orm import relationship

from shared.db.config import Base


class AssetTransactionTable(Base):
    """
    Tracks individual transactions (purchases, sales, dividends) for assets.
    Used to calculate weighted average purchase price (PRUM) and maintain transaction history.
    """

    __tablename__ = "asset_transactions"

    id = Column(Integer, primary_key=True, index=True)
    asset_id = Column(
        Integer, ForeignKey("stocks.id", ondelete="CASCADE"), nullable=False
    )

    # Transaction details
    transaction_type = Column(
        String(20), nullable=False
    )  # 'buy', 'sell', 'dividend', etc.
    timestamp = Column(DateTime(timezone=True), nullable=False)
    quantity = Column(Numeric(20, 10), nullable=False)  # Amount transacted
    price = Column(Numeric(20, 10), nullable=False)  # Price per unit
    total_cost = Column(Numeric(20, 10), nullable=False)  # Total transaction value
    order_id = Column(
        String(50), nullable=True
    )  # External reference (Binance, broker, etc.)

    # Record metadata
    created_at = Column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    # Relationship
    asset = relationship("AssetTable", back_populates="transactions")

    # Index for efficient queries
    __table_args__ = (Index("idx_asset_timestamp", "asset_id", "timestamp"),)
