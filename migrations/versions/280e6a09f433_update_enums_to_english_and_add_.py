"""update_enums_to_english_and_add_delivery_fields.py

Revision ID: 280e6a09f433
Revises: bef26d0f1862
Create Date: 2025-05-14 00:48:24.116302

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision: str = '280e6a09f433'
down_revision: Union[str, None] = 'bef26d0f1862'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    # Обновляем status в таблице order
    op.alter_column(
        'order', 'status',
        type_=mysql.ENUM('new', 'processing', 'delivering', 'completed', 'cancelled'),
        existing_type=mysql.ENUM('новый', 'в сборке', 'в пути', 'выполнен'),
        server_default='new'
    )

    # 2. Обновляем delivery_type в таблице order
    op.alter_column(
        'order', 'delivery_type',
        type_=mysql.ENUM('courier', 'pickup'),
        existing_type=mysql.ENUM('самовывоз', 'доставка до дома'),
        server_default='pickup'
    )

    # 3. Добавляем новые колонки в таблицу order
    op.add_column('order', sa.Column('delivery_comment', sa.String(length=500), nullable=True))
    op.add_column('order', sa.Column('preferred_delivery_date', sa.Date(), nullable=True))
    op.add_column('order', sa.Column('preferred_delivery_time_slot', sa.String(50), nullable=True))
    op.add_column('order', sa.Column('actual_delivery_slot', sa.String(50), nullable=True))

    # 4. Создаем таблицу delivery_time_slot
    op.create_table(
        'delivery_time_slot',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('time_slot', sa.String(50), nullable=False),
        sa.Column('max_orders', sa.Integer(), server_default='5', nullable=False),
        sa.Column('current_orders', sa.Integer(), server_default='0', nullable=False),
        sa.Column('status', mysql.ENUM('available', 'limited', 'unavailable'),
                  server_default='available', nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('date', 'time_slot', name='uq_date_time_slot')
    )

    # 5. Создаем индекс для быстрого поиска доступных слотов
    op.create_index('idx_delivery_slot_availability', 'delivery_time_slot', ['date', 'status'])

    # 6. Обновляем данные для соответствия новым enum (для MySQL)
    op.execute("""
        UPDATE `order` 
        SET status = CASE status
            WHEN 'новый' THEN 'new'
            WHEN 'в сборке' THEN 'processing'
            WHEN 'в пути' THEN 'delivering'
            WHEN 'выполнен' THEN 'completed'
            ELSE 'new'
        END
    """)

    op.execute("""
        UPDATE `order` 
        SET delivery_type = CASE delivery_type
            WHEN 'доставка до дома' THEN 'courier'
            WHEN 'самовывоз' THEN 'pickup'
            ELSE 'pickup'
        END
    """)

def downgrade():
    # 1. Удаляем индекс
    op.drop_index('idx_delivery_slot_availability', table_name='delivery_time_slot')

    # 2. Удаляем таблицу delivery_time_slot
    op.drop_table('delivery_time_slot')

    # 3. Удаляем добавленные колонки из order
    op.drop_column('order', 'actual_delivery_slot')
    op.drop_column('order', 'preferred_delivery_time_slot')
    op.drop_column('order', 'preferred_delivery_date')
    op.drop_column('order', 'delivery_comment')

    # 4. Возвращаем старые enum значения
    op.alter_column(
        'order', 'status',
        type_=mysql.ENUM('новый', 'в сборке', 'в пути', 'выполнен'),
        existing_type=mysql.ENUM('new', 'processing', 'delivering', 'completed', 'cancelled'),
        server_default='новый'
    )

    op.alter_column(
        'order', 'delivery_type',
        type_=mysql.ENUM('самовывоз', 'доставка до дома'),
        existing_type=mysql.ENUM('courier', 'pickup'),
        server_default='самовывоз'
    )

    # 5. Обновляем данные обратно к русским значениям
    op.execute("""
        UPDATE `order` 
        SET status = CASE status
            WHEN 'new' THEN 'новый'
            WHEN 'processing' THEN 'в сборке'
            WHEN 'delivering' THEN 'в пути'
            WHEN 'completed' THEN 'выполнен'
            WHEN 'cancelled' THEN 'новый'
            ELSE 'новый'
        END
    """)

    op.execute("""
        UPDATE `order` 
        SET delivery_type = CASE delivery_type
            WHEN 'courier' THEN 'доставка до дома'
            WHEN 'pickup' THEN 'самовывоз'
            ELSE 'самовывоз'
        END
    """)
