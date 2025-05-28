from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '6ce44536ccad'
down_revision: Union[str, None] = 'af1b796c1e10'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    # Для таблицы Drink
    op.alter_column(
        'drink', 'productDescription',
        new_column_name='product_description',
        existing_type=sa.Text(),  # <-- ставим Text()
        existing_nullable=True
    )
    op.alter_column(
        'drink', 'imgSrc',
        new_column_name='img_src',
        existing_type=sa.String(length=255),  # imgSrc всё равно короткая строка
        existing_nullable=True
    )

    # Для таблицы Section
    op.alter_column(
        'section', 'imgSrc',
        new_column_name='img_src',
        existing_type=sa.String(length=255),
        existing_nullable=True
    )

    # Для таблицы DrinkVolumePrice
    op.alter_column(
        'drinkvolumeprice', 'imgSrc',
        new_column_name='img_src',
        existing_type=sa.String(length=255),
        existing_nullable=True
    )


def downgrade():
    # Возвращаем старые названия
    op.alter_column(
        'drink', 'product_description',
        new_column_name='productDescription',
        existing_type=sa.Text(),  # обратно Text()
        existing_nullable=True
    )
    op.alter_column(
        'drink', 'img_src',
        new_column_name='imgSrc',
        existing_type=sa.String(length=255),
        existing_nullable=True
    )
    op.alter_column(
        'section', 'img_src',
        new_column_name='imgSrc',
        existing_type=sa.String(length=255),
        existing_nullable=True
    )
    op.alter_column(
        'drinkvolumeprice', 'img_src',
        new_column_name='imgSrc',
        existing_type=sa.String(length=255),
        existing_nullable=True
    )
