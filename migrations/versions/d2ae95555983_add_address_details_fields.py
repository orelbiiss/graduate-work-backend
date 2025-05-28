"""add address details fields

Revision ID: d2ae95555983
Revises: 030152ad4d2a
Create Date: 2025-05-02 03:11:53.379735

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision: str = 'd2ae95555983'
down_revision: Union[str, None] = '030152ad4d2a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.add_column('address', sa.Column('building', sa.String(length=50), nullable=True))
    op.add_column('address', sa.Column('liter', sa.String(length=10), nullable=True))
    op.add_column('address', sa.Column('block', sa.String(length=50), nullable=True))

def downgrade():
    op.drop_column('address', 'building')
    op.drop_column('address', 'liter')
    op.drop_column('address', 'block')
