from sqlalchemy import Column, Float, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from src.config import Base


class StockTable(Base):
    __tablename__ = "stocks"

    id = Column(Integer, primary_key=True, index=True)
    fund_id = Column(
        Integer, ForeignKey("funds.id", ondelete="CASCADE"), nullable=False
    )
    symbol = Column(String(20), nullable=False)
    parts_number = Column(Float, nullable=False)
    prum = Column(Float, nullable=False)
    current_repartition = Column(Float, nullable=False)
    target_repartition = Column(Float, nullable=False)
    arbitration_threshold = Column(Float, nullable=False)
    threshold_to_alert = Column(Float, nullable=False)

    fund = relationship("FundTable", back_populates="stocks")
