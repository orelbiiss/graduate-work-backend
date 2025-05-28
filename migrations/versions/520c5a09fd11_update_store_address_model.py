"""update_store_address_model

Revision ID: 520c5a09fd11
Revises: 6c4f5b9b370f
Create Date: 2025-05-15 19:58:04.096134

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '520c5a09fd11'
down_revision: Union[str, None] = '6c4f5b9b370f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    # Для MySQL нужно сначала добавить новую колонку, затем перенести данные, затем удалить старую

    # 1. Добавить колонку house с указанием длины
    op.add_column('storeaddress', sa.Column('house', sa.String(length=50)))

    # 2. Перенести данные из building в house
    op.execute("UPDATE storeaddress SET house = building")

    # 3. Удалить колонку building
    op.drop_column('storeaddress', 'building')

    # 4. Удалить колонку entrance
    op.drop_column('storeaddress', 'entrance')

    # 5. Добавить новые колонки с указанием длин
    op.add_column('storeaddress', sa.Column('full_address', sa.String(length=500), nullable=False))
    op.add_column('storeaddress', sa.Column('created_at', sa.DateTime(), nullable=True))

    # 6. Заполнить full_address и created_at
    op.execute("""
            UPDATE storeaddress 
            SET full_address = CONCAT(street, ', ', house, 
                                   IF(apartment IS NOT NULL, CONCAT(', кв. ', apartment), '')),
                created_at = UTC_TIMESTAMP()
        """)

    # 7. Сделать created_at NOT NULL
    op.alter_column('storeaddress', 'created_at', nullable=False,
                    existing_type=sa.DateTime())


def downgrade():
    # Вернуть изменения при откате миграции

    # 1. Добавить обратно колонку building с указанием длины
    op.add_column('storeaddress', sa.Column('building', sa.String(length=50)))

    # 2. Перенести данные из house в building
    op.execute("UPDATE storeaddress SET building = house")

    # 3. Удалить колонку house
    op.drop_column('storeaddress', 'house')

    # 4. Добавить колонку entrance с указанием длины
    op.add_column('storeaddress', sa.Column('entrance', sa.String(length=20), nullable=True))

    # 5. Удалить добавленные колонки
    op.drop_column('storeaddress', 'full_address')
    op.drop_column('storeaddress', 'created_at')
