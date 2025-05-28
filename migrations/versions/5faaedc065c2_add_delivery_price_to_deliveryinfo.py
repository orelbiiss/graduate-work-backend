"""Add delivery_price to deliveryinfo

Revision ID: 5faaedc065c2
Revises: 15dd80d7a031
Create Date: 2025-05-20 20:33:38.420119

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5faaedc065c2'
down_revision: Union[str, None] = '15dd80d7a031'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade():
    op.add_column('deliveryinfo', sa.Column('delivery_price', sa.Integer(), nullable=False, server_default="0"))


def downgrade():
    op.drop_column('deliveryinfo', 'delivery_price')
