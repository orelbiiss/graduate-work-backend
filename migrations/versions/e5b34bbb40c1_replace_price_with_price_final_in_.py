"""replace price with price_final in orderitem

Revision ID: e5b34bbb40c1
Revises: e5bfeb005ef9
Create Date: 2025-05-07 01:23:42.308699

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision: str = 'e5b34bbb40c1'
down_revision: Union[str, None] = 'e5bfeb005ef9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    with op.batch_alter_table('orderitem', schema=None) as batch_op:

        batch_op.drop_column('price')

        batch_op.add_column(sa.Column('price_final', sa.Integer(), nullable=False))


def downgrade():
    with op.batch_alter_table('orderitem', schema=None) as batch_op:
        batch_op.drop_column('price_final')
        # При необходимости можно восстановить 'price'
        # batch_op.add_column(sa.Column('price', sa.Integer(), nullable=False))


