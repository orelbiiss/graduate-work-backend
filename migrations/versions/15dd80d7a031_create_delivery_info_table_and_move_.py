"""Create delivery_info table and move delivery data

Revision ID: 15dd80d7a031
Revises: f43a9e69b7f2
Create Date: 2025-05-19 21:46:58.246583

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '15dd80d7a031'
down_revision: Union[str, None] = 'f43a9e69b7f2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    # 1. Создаем новую таблицу deliveryinfo
    op.create_table(
        'deliveryinfo',
        sa.Column('id', sa.Integer(), nullable=False, primary_key=True),
        sa.Column('order_id', sa.Integer(),
                sa.ForeignKey('order.id', ondelete='CASCADE'),
                nullable=False, unique=True),
        sa.Column('full_address', sa.String(length=500), nullable=True),
        sa.Column('delivery_comment', sa.String(length=500), nullable=True),
        sa.Column('delivery_date', sa.Date(), nullable=True),
        sa.Column('delivery_time', sa.String(length=50), nullable=True),
        sa.Column('customer_name', sa.String(length=100), nullable=True),
        sa.Column('customer_phone', sa.String(length=20), nullable=True),
    )

    # 2. Переносим данные из order в deliveryinfo
    op.execute("""
        INSERT INTO deliveryinfo (
            order_id, 
            full_address, 
            delivery_comment, 
            delivery_date, 
            delivery_time, 
            customer_name, 
            customer_phone
        )
        SELECT 
            id, 
            full_address, 
            delivery_comment, 
            delivery_date, 
            delivery_time, 
            customer_name, 
            customer_phone
        FROM `order`
        WHERE 
            full_address IS NOT NULL OR
            delivery_comment IS NOT NULL OR
            delivery_date IS NOT NULL OR
            delivery_time IS NOT NULL OR
            customer_name IS NOT NULL OR
            customer_phone IS NOT NULL
    """)

    # 3. Удаляем старые колонки из order
    op.drop_column('order', 'full_address')
    op.drop_column('order', 'delivery_comment')
    op.drop_column('order', 'delivery_date')
    op.drop_column('order', 'delivery_time')
    op.drop_column('order', 'customer_name')
    op.drop_column('order', 'customer_phone')

def downgrade():
    # 1. Возвращаем колонки в order
    op.add_column('order', sa.Column('full_address', sa.String(length=500), nullable=True))
    op.add_column('order', sa.Column('delivery_comment', sa.String(length=500), nullable=True))
    op.add_column('order', sa.Column('delivery_date', sa.Date(), nullable=True))
    op.add_column('order', sa.Column('delivery_time', sa.String(length=50), nullable=True))
    op.add_column('order', sa.Column('customer_name', sa.String(length=100), nullable=True))
    op.add_column('order', sa.Column('customer_phone', sa.String(length=20), nullable=True))

    # 2. Переносим данные обратно из deliveryinfo в order
    op.execute("""
        UPDATE `order` o
        SET 
            full_address = di.full_address,
            delivery_comment = di.delivery_comment,
            delivery_date = di.delivery_date,
            delivery_time = di.delivery_time,
            customer_name = di.customer_name,
            customer_phone = di.customer_phone
        FROM deliveryinfo di
        WHERE di.order_id = o.id
    """)

    # 3. Удаляем таблицу deliveryinfo
    op.drop_table('deliveryinfo')
