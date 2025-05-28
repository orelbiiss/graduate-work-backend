"""change_all_enums_to_lowercase

Revision ID: 64a5867df967
Revises: 87dbff65b77f
Create Date: 2025-05-14 03:23:39.004432

"""
from typing import Sequence, Union

from alembic import op
from sqlalchemy.dialects import mysql


# revision identifiers, used by Alembic.
revision: str = '64a5867df967'
down_revision: Union[str, None] = '87dbff65b77f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    # 1. Изменяем OrderStatus (new, processing, delivering, completed, cancelled)
    op.alter_column(
        'order',
        'status',
        type_=mysql.ENUM('new', 'processing', 'delivering', 'completed', 'cancelled', name='orderstatus'),
        existing_type=mysql.ENUM('NEW', 'PROCESSING', 'DELIVERING', 'COMPLETED', 'CANCELLED', name='orderstatus')
    )

    # 2. Изменяем DeliveryType (courier, pickup)
    op.alter_column(
        'order',
        'delivery_type',
        type_=mysql.ENUM('courier', 'pickup', name='deliverytype'),
        existing_type=mysql.ENUM('COURIER', 'PICKUP', name='deliverytype')
    )

    # 3. Изменяем DeliveryTimeSlotStatus (available, limited, unavailable)
    op.alter_column(
        'deliverytimeslot',
        'status',
        type_=mysql.ENUM('available', 'limited', 'unavailable', name='deliverytimeslotstatus'),
        existing_type=mysql.ENUM('AVAILABLE', 'LIMITED', 'UNAVAILABLE', name='deliverytimeslotstatus')
    )

def downgrade():
    # Откат OrderStatus (NEW, PROCESSING, ...)
    op.alter_column(
        'order',
        'status',
        type_=mysql.ENUM('NEW', 'PROCESSING', 'DELIVERING', 'COMPLETED', 'CANCELLED', name='orderstatus'),
        existing_type=mysql.ENUM('new', 'processing', 'delivering', 'completed', 'cancelled', name='orderstatus')
    )

    # Откат DeliveryType (COURIER, PICKUP)
    op.alter_column(
        'order',
        'delivery_type',
        type_=mysql.ENUM('COURIER', 'PICKUP', name='deliverytype'),
        existing_type=mysql.ENUM('courier', 'pickup', name='deliverytype')
    )

    # Откат DeliveryTimeSlotStatus (AVAILABLE, LIMITED, UNAVAILABLE)
    op.alter_column(
        'deliverytimeslot',
        'status',
        type_=mysql.ENUM('AVAILABLE', 'LIMITED', 'UNAVAILABLE', name='deliverytimeslotstatus'),
        existing_type=mysql.ENUM('available', 'limited', 'unavailable', name='deliverytimeslotstatus')
    )
