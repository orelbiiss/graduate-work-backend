"""remove_apartment_from_storeaddress

Revision ID: f43a9e69b7f2
Revises: 520c5a09fd11
Create Date: 2025-05-15 20:16:24.895924

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f43a9e69b7f2'
down_revision: Union[str, None] = '520c5a09fd11'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    # Удаляем колонку apartment
    op.drop_column('storeaddress', 'apartment')


def downgrade():
    # Восстанавливаем колонку apartment при откате
    op.add_column('storeaddress',
                  sa.Column('apartment', sa.String(length=20), nullable=True))
