"""add unique constraint on stocks.symbol and currency column

Revision ID: a1f7c2e9d4b3
Revises: 3b2342156055
Create Date: 2026-05-17 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a1f7c2e9d4b3"
down_revision: Union[str, Sequence[str], None] = "3b2342156055"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "stocks",
        sa.Column(
            "currency",
            sa.String(length=3),
            nullable=False,
            server_default="USD",
        ),
    )
    op.drop_index(op.f("ix_stocks_symbol"), table_name="stocks")
    op.create_index(op.f("ix_stocks_symbol"), "stocks", ["symbol"], unique=True)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f("ix_stocks_symbol"), table_name="stocks")
    op.create_index(op.f("ix_stocks_symbol"), "stocks", ["symbol"], unique=False)
    op.drop_column("stocks", "currency")
