"""make user_id optional in Cart, add session_key and created_at

Revision ID: bef26d0f1862
Revises: 5de693c59968
Create Date: 2025-05-11 21:23:17.334190

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'bef26d0f1862'
down_revision: Union[str, None] = '5de693c59968'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    # Изменяем user_id: делаем nullable
    op.alter_column('cart', 'user_id',
        existing_type=sa.Integer(),
        nullable=True
    )

    # Добавляем session_key
    sa.Column('session_key', sa.String(length=255), unique=True, nullable=True)

    # Добавляем created_at
    op.add_column('cart', sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')))

def downgrade():
    # Удаляем created_at
    op.drop_column('cart', 'created_at')

    # Удаляем session_key
    op.drop_column('cart', 'session_key')

    # Возвращаем user_id в non-nullable
    op.alter_column('cart', 'user_id',
        existing_type=sa.Integer(),
        nullable=False
    )
