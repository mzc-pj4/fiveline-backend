"""add product_name and product_price cache to cart_items

Revision ID: a1b2c3d4e5f6
Revises: 36a07050e5c7
Create Date: 2026-06-08 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = '36a07050e5c7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('cart_items', sa.Column('product_name', sa.String(length=500), nullable=True), schema='order_schema')
    op.add_column('cart_items', sa.Column('product_price', sa.Numeric(precision=12, scale=2), nullable=True), schema='order_schema')


def downgrade() -> None:
    op.drop_column('cart_items', 'product_price', schema='order_schema')
    op.drop_column('cart_items', 'product_name', schema='order_schema')
