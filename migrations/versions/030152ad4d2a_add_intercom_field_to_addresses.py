"""add_intercom_field_to_addresses

Revision ID: 030152ad4d2a
Revises: 6ce44536ccad
Create Date: 2025-05-02 00:05:11.568214

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '030152ad4d2a'
down_revision: Union[str, None] = '6ce44536ccad'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.add_column('address',
                  sa.Column('intercom', sa.String(length=50), nullable=True))


def downgrade():
    op.drop_column('address', 'intercom')
