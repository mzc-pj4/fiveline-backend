"""add phone to users

Revision ID: b0001
Revises: a8e156d5e859
Create Date: 2026-06-07 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'b0001'
down_revision: Union[str, Sequence[str], None] = 'a8e156d5e859'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('users', sa.Column('phone', sa.String(length=20), nullable=True), schema='user_schema')


def downgrade() -> None:
    op.drop_column('users', 'phone', schema='user_schema')
