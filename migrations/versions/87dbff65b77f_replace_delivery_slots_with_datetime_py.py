"""replace_delivery_slots_with_datetime.py

Revision ID: 87dbff65b77f
Revises: 280e6a09f433
Create Date: 2025-05-14 01:05:40.259851

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '87dbff65b77f'
down_revision: Union[str, None] = '280e6a09f433'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    # 1. Удаляем старые поля, если они существуют
    op.drop_column('order', 'preferred_delivery_date', if_exists=True)
    op.drop_column('order', 'preferred_delivery_time_slot', if_exists=True)
    op.drop_column('order', 'actual_delivery_slot', if_exists=True)

    # 3. Добавляем новые поля
    op.add_column('order', sa.Column('delivery_date', sa.Date(), nullable=True))
    op.add_column('order', sa.Column('delivery_time', sa.Time(), nullable=True))


def downgrade():
    # 1. Удаляем новые поля
    op.drop_column('order', 'delivery_time')
    op.drop_column('order', 'delivery_date')

    # 2. Восстанавливаем старые поля (опционально, если нужно полное откатывание)
    op.add_column('order', sa.Column('preferred_delivery_date', sa.Date(), nullable=True))
    op.add_column('order', sa.Column('preferred_delivery_time_slot', sa.String(50), nullable=True))
    op.add_column('order', sa.Column('actual_delivery_slot', sa.String(50), nullable=True))