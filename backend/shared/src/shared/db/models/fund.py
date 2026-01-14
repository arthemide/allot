from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Integer, String
from sqlalchemy.orm import relationship

from shared.db.config import Base


class FundTable(Base):
    __tablename__ = "funds"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    created_at = Column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationship to assets (previously stocks)
    assets = relationship(
        "AssetTable", back_populates="fund", cascade="all, delete-orphan"
    )

    # Keep old relationship name for backward compatibility
    @property
    def stocks(self):
        return self.assets
