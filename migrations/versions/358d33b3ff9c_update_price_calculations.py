"""update_price_calculations

Revision ID: 358d33b3ff9c
Revises: 6eeac7db082a
Create Date: 2025-05-06 23:12:40.552458

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '358d33b3ff9c'
down_revision: Union[str, None] = '6eeac7db082a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():

    # 4. Заполняем price_original (используем price)
    op.execute("UPDATE orderitem SET price_original = price")

    # 5. Делаем колонку обязательной
    op.alter_column(
        'orderitem',
        'price_original',
        existing_type=sa.Integer(),
        nullable=False
    )


def downgrade():
    # 1. Возвращаем старое название
    op.alter_column('order', 'items_total', new_column_name='total_price')

    # 2. Удаляем новые колонки
    op.drop_column('order', 'items_subtotal')
    op.drop_column('order', 'items_discount')

    # 3. Восстанавливаем price из price_original
    op.execute("UPDATE orderitem SET price = price_original")
    op.drop_column('orderitem', 'price_original')