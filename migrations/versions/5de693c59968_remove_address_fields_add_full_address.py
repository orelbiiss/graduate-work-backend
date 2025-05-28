"""remove address fields, add full_address

Revision ID: 5de693c59968
Revises: 700cda4fbd8c
Create Date: 2025-05-07 04:41:23.589568

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision: str = '5de693c59968'
down_revision: Union[str, None] = '700cda4fbd8c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.add_column('order', sa.Column('full_address', sa.String(length=500), nullable=True))
    op.drop_column('order', 'delivery_street')
    op.drop_column('order', 'delivery_house')
    op.drop_column('order', 'delivery_entrance')
    op.drop_column('order', 'delivery_floor')
    op.drop_column('order', 'delivery_apartment')


def downgrade():
    op.add_column('order', sa.Column('delivery_apartment', sa.String(), nullable=True))
    op.add_column('order', sa.Column('delivery_floor', sa.String(), nullable=True))
    op.add_column('order', sa.Column('delivery_entrance', sa.String(), nullable=True))
    op.add_column('order', sa.Column('delivery_house', sa.String(), nullable=True))
    op.add_column('order', sa.Column('delivery_street', sa.String(), nullable=True))
    op.drop_column('order', 'full_address')
