"""add_item_total_fields

Revision ID: 33e5e868deec
Revises: e5b34bbb40c1
Create Date: 2025-05-07 03:07:04.017543

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '33e5e868deec'
down_revision: Union[str, None] = 'e5b34bbb40c1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade():
    # Добавляем поля в cartitem
    op.add_column('cartitem', sa.Column('item_subtotal', sa.Integer(), server_default='0', nullable=False))
    op.add_column('cartitem', sa.Column('item_discount', sa.Integer(), server_default='0', nullable=False))
    op.add_column('cartitem', sa.Column('item_total', sa.Integer(), server_default='0', nullable=False))

    # Добавляем поля в orderitem
    op.add_column('orderitem', sa.Column('item_subtotal', sa.Integer(), nullable=False))
    op.add_column('orderitem', sa.Column('item_discount', sa.Integer(), nullable=False))
    op.add_column('orderitem', sa.Column('item_total', sa.Integer(), nullable=False))

    # Обновляем существующие записи (если нужно)
    # Для cartitem
    op.execute("""
        UPDATE cartitem 
        SET item_subtotal = quantity * (
            SELECT price FROM drinkvolumeprice WHERE id = cartitem.drink_volume_price_id
        ),
        item_discount = quantity * (
            SELECT (price * (COALESCE(sale, 0)/100) 
            FROM drinkvolumeprice 
            WHERE id = cartitem.drink_volume_price_id
        ),
        item_total = item_subtotal - item_discount
    """)

    # Для orderitem (используем сохраненные price_original и price_final)
    op.execute("""
        UPDATE orderitem 
        SET item_subtotal = price_original * quantity,
            item_discount = (price_original - price_final) * quantity,
            item_total = price_final * quantity
    """)

def downgrade():
    # Удаляем поля из cartitem
    op.drop_column('cartitem', 'item_subtotal')
    op.drop_column('cartitem', 'item_discount')
    op.drop_column('cartitem', 'item_total')

    # Удаляем поля из orderitem
    op.drop_column('orderitem', 'item_subtotal')
    op.drop_column('orderitem', 'item_discount')
    op.drop_column('orderitem', 'item_total')
