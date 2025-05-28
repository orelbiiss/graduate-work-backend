"""change_deliverytimeslotstatus_enum_to_lowercase

Revision ID: 6c4f5b9b370f
Revises: c7a83ca0a87d
Create Date: 2025-05-14 04:21:51.215944

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6c4f5b9b370f'
down_revision: Union[str, None] = 'c7a83ca0a87d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.alter_column(
        'deliverytimeslot',
        'status',
        type_=sa.Enum('available', 'limited', 'unavailable', name='deliverytimeslotstatus'),
        existing_type=sa.Enum('AVAILABLE', 'LIMITED', 'UNAVAILABLE', name='deliverytimeslotstatus')
    )

def downgrade():
    op.alter_column(
        'deliverytimeslot',
        'status',
        type_=sa.Enum('AVAILABLE', 'LIMITED', 'UNAVAILABLE', name='deliverytimeslotstatus'),
        existing_type=sa.Enum('available', 'limited', 'unavailable', name='deliverytimeslotstatus')
    )
