"""change_deliverytimeslotstatus_to_lowercase

Revision ID: c7a83ca0a87d
Revises: 64a5867df967
Create Date: 2025-05-14 03:27:14.178765

"""
from typing import Sequence, Union

from alembic import op
from sqlalchemy.dialects import mysql


# revision identifiers, used by Alembic.
revision: str = 'c7a83ca0a87d'
down_revision: Union[str, None] = '64a5867df967'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    # Меняем ENUM на lowercase-значения
    op.alter_column(
        'deliverytimeslot',
        'status',
        type_=mysql.ENUM('available', 'limited', 'unavailable', name='deliverytimeslotstatus'),
        existing_type=mysql.ENUM('AVAILABLE', 'LIMITED', 'UNAVAILABLE', name='deliverytimeslotstatus')
    )

def downgrade():
    # Возвращаем UPPERCASE-значения
    op.alter_column(
        'deliverytimeslot',
        'status',
        type_=mysql.ENUM('AVAILABLE', 'LIMITED', 'UNAVAILABLE', name='deliverytimeslotstatus'),
        existing_type=mysql.ENUM('available', 'limited', 'unavailable', name='deliverytimeslotstatus')
    )
