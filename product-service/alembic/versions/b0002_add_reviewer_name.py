"""add reviewer_name to reviews

Revision ID: b0002
Revises: b0001
Create Date: 2026-06-08 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'b0002'
down_revision: Union[str, Sequence[str], None] = 'b0001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    cols = {r[0] for r in conn.execute(sa.text(
        "SELECT column_name FROM information_schema.columns "
        "WHERE table_schema='product_schema' AND table_name='reviews'"
    ))}
    if 'reviewer_name' not in cols:
        op.add_column('reviews', sa.Column('reviewer_name', sa.String(length=100), nullable=True), schema='product_schema')


def downgrade() -> None:
    op.drop_column('reviews', 'reviewer_name', schema='product_schema')
