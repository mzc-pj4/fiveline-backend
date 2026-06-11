"""add brand and original_price to products

Revision ID: b0001
Revises: fe429ccc5ab8
Create Date: 2026-06-07 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'b0001'
down_revision: Union[str, Sequence[str], None] = 'fe429ccc5ab8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    cols = {r[0] for r in conn.execute(sa.text(
        "SELECT column_name FROM information_schema.columns "
        "WHERE table_schema='product_schema' AND table_name='products'"
    ))}
    if 'brand' not in cols:
        op.add_column('products', sa.Column('brand', sa.String(length=100), nullable=True), schema='product_schema')
    if 'original_price' not in cols:
        op.add_column('products', sa.Column('original_price', sa.Numeric(precision=12, scale=2), nullable=True), schema='product_schema')


def downgrade() -> None:
    op.drop_column('products', 'original_price', schema='product_schema')
    op.drop_column('products', 'brand', schema='product_schema')
