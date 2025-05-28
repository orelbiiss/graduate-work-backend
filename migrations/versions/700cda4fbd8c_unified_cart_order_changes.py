"""unified_cart_order_changes

Revision ID: 700cda4fbd8c
Revises: 33e5e868deec
Create Date: 2025-05-07 03:14:43.080693

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '700cda4fbd8c'
down_revision: Union[str, None] = '33e5e868deec'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    # Добавляем новые поля в cartitem
    op.add_column('cartitem',
        sa.Column('item_subtotal', sa.Integer(), server_default='0', nullable=False))
    op.add_column('cartitem',
        sa.Column('item_discount', sa.Integer(), server_default='0', nullable=False))
    op.add_column('cartitem',
        sa.Column('item_total', sa.Integer(), server_default='0', nullable=False))

    # Добавляем новые поля в orderitem
    op.add_column('orderitem',
        sa.Column('item_subtotal', sa.Integer(), nullable=False))
    op.add_column('orderitem',
        sa.Column('item_discount', sa.Integer(), nullable=False))
    op.add_column('orderitem',
        sa.Column('item_total', sa.Integer(), nullable=False))

    # Переименовываем поля в cart
    op.alter_column('cart', 'items_subtotal', new_column_name='cart_subtotal',
                   existing_type=sa.Integer(), server_default='0')
    op.alter_column('cart', 'items_discount', new_column_name='cart_discount',
                   existing_type=sa.Integer(), server_default='0')
    op.alter_column('cart', 'items_total', new_column_name='cart_total',
                   existing_type=sa.Integer(), server_default='0')

    # Переименовываем поля в order
    op.alter_column('order', 'items_subtotal', new_column_name='order_subtotal',
                   existing_type=sa.Integer())
    op.alter_column('order', 'items_discount', new_column_name='order_discount',
                   existing_type=sa.Integer())
    op.alter_column('order', 'items_total', new_column_name='order_total',
                   existing_type=sa.Integer())

    # Обновляем данные для новых полей
    op.execute("""
        UPDATE cartitem 
        SET item_subtotal = quantity * (
            SELECT price FROM drinkvolumeprice WHERE id = cartitem.drink_volume_price_id
        ),
        item_discount = quantity * (
            SELECT (price * COALESCE(sale, 0)/100) 
            FROM drinkvolumeprice 
            WHERE id = cartitem.drink_volume_price_id
        ),
        item_total = item_subtotal - item_discount
    """)

    op.execute("""
        UPDATE orderitem 
        SET item_subtotal = price_original * quantity,
            item_discount = (price_original - price_final) * quantity,
            item_total = price_final * quantity
    """)

def downgrade():
    # Возвращаем старые имена полей в cart
    op.alter_column('cart', 'cart_subtotal', new_column_name='items_subtotal',
                   existing_type=sa.Integer())
    op.alter_column('cart', 'cart_discount', new_column_name='items_discount',
                   existing_type=sa.Integer())
    op.alter_column('cart', 'cart_total', new_column_name='items_total',
                   existing_type=sa.Integer())

    # Возвращаем старые имена полей в order
    op.alter_column('order', 'order_subtotal', new_column_name='items_subtotal',
                   existing_type=sa.Integer())
    op.alter_column('order', 'order_discount', new_column_name='items_discount',
                   existing_type=sa.Integer())
    op.alter_column('order', 'order_total', new_column_name='items_total',
                   existing_type=sa.Integer())

    # Удаляем добавленные поля
    op.drop_column('cartitem', 'item_subtotal')
    op.drop_column('cartitem', 'item_discount')
    op.drop_column('cartitem', 'item_total')

    op.drop_column('orderitem', 'item_subtotal')
    op.drop_column('orderitem', 'item_discount')
    op.drop_column('orderitem', 'item_total')
