from sqlalchemy import Column, Float, ForeignKey, Integer, String, Numeric, Text, Index
from sqlalchemy.orm import relationship

from shared.db.config import Base


class AssetTable(Base):
    """
    Unified asset table for stocks, crypto, and other asset types.
    Previously known as StockTable, extended to support multiple asset types.
    """
    __tablename__ = "stocks"  # Keep existing table name for backward compatibility

    id = Column(Integer, primary_key=True, index=True)
    fund_id = Column(
        Integer, ForeignKey("funds.id", ondelete="CASCADE"), nullable=True
    )  # Made nullable for standalone crypto assets

    # Asset identification
    name = Column(String(255), nullable=False)
    symbol = Column(String(20), nullable=False)
    asset_type = Column(String(20), nullable=False, default='stock')  # 'stock', 'crypto', 'bond', etc.

    # Quantity
    # For stocks: manually maintained current quantity
    # For crypto with transaction tracking: historical quantity (before bot started tracking)
    shares_number = Column(Float, nullable=False)

    # Cost and allocation
    cost = Column(Float, nullable=False)
    current_repartition = Column(Float, nullable=False)
    target_repartition = Column(Float, nullable=True)
    arbitration_threshold = Column(Float, nullable=False)
    threshold_to_alert = Column(Float, nullable=False)

    # NEW: Historical tracking fields for assets with purchase history
    base_prum = Column(Numeric(20, 10), nullable=True)  # Historical average purchase price (for PRUM calculation)

    # Relationships
    fund = relationship("FundTable", back_populates="assets")
    transactions = relationship(
        "AssetTransactionTable", back_populates="asset", cascade="all, delete-orphan"
    )

    # Backward compatibility property
    @property
    def quantity(self):
        """Alias for shares_number for unified API"""
        return self.shares_number

    @quantity.setter
    def quantity(self, value):
        """Setter for quantity property"""
        self.shares_number = value

    # Create index on symbol and asset_type for fast lookups
    __table_args__ = (
        Index('idx_symbol_asset_type', 'symbol', 'asset_type'),
    )
