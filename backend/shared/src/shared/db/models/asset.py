from sqlalchemy import Column, Float, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import relationship

from shared.db.config import Base


class AssetTable(Base):
    """Unified asset table for stocks and crypto assets."""

    __tablename__ = "stocks"

    id = Column(Integer, primary_key=True, index=True)
    fund_id = Column(Integer, ForeignKey("funds.id", ondelete="CASCADE"), nullable=True)

    # Asset identification
    name = Column(String(255), nullable=False)
    symbol = Column(String(20), nullable=False, index=True, unique=True)
    currency = Column(String(3), nullable=False, server_default="USD")

    shares_number = Column(Float, nullable=False)  # Pre-bot historical quantity
    cost = Column(Float, nullable=False)
    current_repartition = Column(Float, nullable=False)
    target_repartition = Column(Float, nullable=True)
    arbitration_threshold = Column(Float, nullable=False)
    threshold_to_alert = Column(Float, nullable=False)
    base_prum = Column(
        Numeric(20, 10), nullable=True
    )  # Pre-bot historical average price

    fund = relationship("FundTable", back_populates="assets")
    transactions = relationship(
        "AssetTransactionTable", back_populates="asset", cascade="all, delete-orphan"
    )
