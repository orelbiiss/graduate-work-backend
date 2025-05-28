"""create_unverified_user_and_remove_is_verified

Revision ID: 345fa90b2c29
Revises: d9800d43a65c
Create Date: 2025-04-27 22:26:47.157349

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = '345fa90b2c29'
down_revision = 'd9800d43a65c'
branch_labels = None
depends_on = None


def upgrade():
    # Создаем таблицу unverified_user
    op.create_table('unverifieduser',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('hashed_password', sa.String(length=255), nullable=False),
        sa.Column('first_name', sa.String(length=255), nullable=False),
        sa.Column('last_name', sa.String(length=255), nullable=False),
        sa.Column('middle_name', sa.String(length=255), nullable=True),
        sa.Column('birth_date', sa.Date(), nullable=True),
        sa.Column('gender', sa.Enum('MALE', 'FEMALE', 'UNSPECIFIED', name='gender'), nullable=True),
        sa.Column('phone', sa.String(length=255), nullable=True),
        sa.Column('role', sa.Enum('USER', 'ADMIN', name='userrole'), nullable=False),
        sa.Column('verification_token', sa.String(length=255), nullable=False),
        sa.Column('token_expires', sa.DateTime(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email')
    )
    op.create_index(op.f('ix_unverifieduser_email'), 'unverifieduser', ['email'], unique=True)

    # Удаляем столбец is_verified из таблицы user
    with op.batch_alter_table('user') as batch_op:
        batch_op.drop_column('is_verified')


def downgrade():
    # Восстанавливаем столбец is_verified
    op.add_column('user',
        sa.Column('is_verified',
                 mysql.TINYINT(display_width=1),
                 autoincrement=False,
                 nullable=False,
                 server_default=sa.text("'0'"))
    )

    # Удаляем таблицу unverified_user
    op.drop_index(op.f('ix_unverifieduser_email'), table_name='unverifieduser')
    op.drop_table('unverifieduser')