"""Add fields to Cart

Revision ID: e5bfeb005ef9
Revises: 358d33b3ff9c
Create Date: 2025-05-06 23:44:26.304160

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision: str = 'e5bfeb005ef9'
down_revision: Union[str, None] = '358d33b3ff9c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Добавление новых полей в таблицу Cart
    op.add_column('cart', sa.Column('items_subtotal', sa.Integer(), nullable=False, default=0))
    op.add_column('cart', sa.Column('items_discount', sa.Integer(), nullable=False, default=0))
    op.add_column('cart', sa.Column('items_total', sa.Integer(), nullable=False, default=0))


def downgrade() -> None:
    # Удаление новых полей при откате миграции
    op.drop_column('cart', 'items_subtotal')
    op.drop_column('cart', 'items_discount')
    op.drop_column('cart', 'items_total')
