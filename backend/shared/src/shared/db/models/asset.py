from decimal import Decimal
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import Float, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from shared.db.config import Base

if TYPE_CHECKING:
    from shared.db.models.fund import FundTable
    from shared.db.models.transaction import AssetTransactionTable


class AssetTable(Base):
    """Unified asset table for stocks and crypto assets."""

    __tablename__ = "stocks"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    fund_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("funds.id", ondelete="CASCADE"), nullable=True
    )

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    symbol: Mapped[str] = mapped_column(
        String(20), nullable=False, index=True, unique=True
    )
    currency: Mapped[str] = mapped_column(
        String(3), nullable=False, server_default="USD"
    )

    shares_number: Mapped[float] = mapped_column(Float, nullable=False)
    cost: Mapped[float] = mapped_column(Float, nullable=False)
    current_repartition: Mapped[float] = mapped_column(Float, nullable=False)
    target_repartition: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    arbitration_threshold: Mapped[float] = mapped_column(Float, nullable=False)
    threshold_to_alert: Mapped[float] = mapped_column(Float, nullable=False)
    base_prum: Mapped[Optional[Decimal]] = mapped_column(Numeric(20, 10), nullable=True)

    fund: Mapped[Optional["FundTable"]] = relationship(  # noqa: F821
        "FundTable", back_populates="assets"
    )
    transactions: Mapped[List["AssetTransactionTable"]] = relationship(  # noqa: F821
        "AssetTransactionTable", back_populates="asset", cascade="all, delete-orphan"
    )
