"""update_address_table_structure

Revision ID: 6eeac7db082a
Revises: d2ae95555983
Create Date: 2025-05-02 06:35:46.652870

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql
from sqlalchemy.engine.reflection import Inspector

# revision identifiers, used by Alembic.
revision: str = '6eeac7db082a'
down_revision: Union[str, None] = 'd2ae95555983'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade():
    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)
    columns = [col['name'] for col in inspector.get_columns('address')]

    # Добавляем новое поле только если оно не существует
    if 'full_address' not in columns:
        op.add_column('address', sa.Column('full_address', sa.String(length=500), nullable=True))

        # Делаем поле обязательным
        with op.batch_alter_table('address') as batch_op:
            batch_op.alter_column('full_address',
                                 existing_type=sa.String(length=500),
                                 nullable=False)

    # Удаляем ненужные колонки (только если они существуют)
    if 'building' in columns:
        op.drop_column('address', 'building')
    if 'liter' in columns:
        op.drop_column('address', 'liter')
    if 'block' in columns:
        op.drop_column('address', 'block')

def downgrade():
    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)
    columns = [col['name'] for col in inspector.get_columns('address')]

    # Восстанавливаем удаленные колонки (только если их нет)
    if 'building' not in columns:
        op.add_column('address', sa.Column('building', mysql.VARCHAR(length=50), nullable=True))
    if 'liter' not in columns:
        op.add_column('address', sa.Column('liter', mysql.VARCHAR(length=10), nullable=True))
    if 'block' not in columns:
        op.add_column('address', sa.Column('block', mysql.VARCHAR(length=50), nullable=True))

    # Удаляем новое поле (если существует)
    if 'full_address' in columns:
        op.drop_column('address', 'full_address')