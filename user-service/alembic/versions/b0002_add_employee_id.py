"""add employee_id to users

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
        "WHERE table_schema='user_schema' AND table_name='users'"
    ))}
    if 'employee_id' not in cols:
        op.add_column('users', sa.Column('employee_id', sa.String(50), nullable=True), schema='user_schema')
        op.create_unique_constraint('uq_users_employee_id', 'users', ['employee_id'], schema='user_schema')


def downgrade() -> None:
    op.drop_constraint('uq_users_employee_id', 'users', schema='user_schema')
    op.drop_column('users', 'employee_id', schema='user_schema')
