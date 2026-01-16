"""unified asset models

Revision ID: 981b1135209c
Revises: 6a3ba15164f3
Create Date: 2026-01-13 12:59:58.397792

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "981b1135209c"
down_revision: Union[str, Sequence[str], None] = "6a3ba15164f3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema to support unified asset model (stocks, crypto, etc.)"""
    # Add new columns to stocks table to support multiple asset types
    op.add_column(
        "stocks",
        sa.Column(
            "asset_type", sa.String(length=20), nullable=False, server_default="stock"
        ),
    )
    op.add_column(
        "stocks",
        sa.Column("base_prum", sa.Numeric(precision=20, scale=10), nullable=True),
    )

    # Make fund_id nullable for standalone crypto assets
    op.alter_column("stocks", "fund_id", existing_type=sa.INTEGER(), nullable=True)

    # Create asset_transactions table
    op.create_table(
        "asset_transactions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("asset_id", sa.Integer(), nullable=False),
        sa.Column("transaction_type", sa.String(length=20), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("quantity", sa.Numeric(precision=20, scale=10), nullable=False),
        sa.Column("price", sa.Numeric(precision=20, scale=10), nullable=False),
        sa.Column("total_cost", sa.Numeric(precision=20, scale=10), nullable=False),
        sa.Column("order_id", sa.String(length=50), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["asset_id"], ["stocks.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create indexes
    op.create_index("idx_symbol_asset_type", "stocks", ["symbol", "asset_type"])
    op.create_index(
        "idx_asset_timestamp", "asset_transactions", ["asset_id", "timestamp"]
    )


def downgrade() -> None:
    """Downgrade schema to remove unified asset model support"""
    # Drop indexes
    op.drop_index("idx_asset_timestamp", table_name="asset_transactions")
    op.drop_index("idx_symbol_asset_type", table_name="stocks")

    # Drop asset_transactions table
    op.drop_table("asset_transactions")

    # Make fund_id not nullable again
    op.alter_column("stocks", "fund_id", existing_type=sa.INTEGER(), nullable=False)

    # Remove new columns from stocks table
    op.drop_column("stocks", "base_prum")
    op.drop_column("stocks", "asset_type")
