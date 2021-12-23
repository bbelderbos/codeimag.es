"""add defaults

Revision ID: 9736cdc8b5e9
Revises: 3e44ae42fad8
Create Date: 2021-12-23 09:59:53.057813

"""
from alembic import op
import sqlalchemy as sa
import sqlmodel
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '9736cdc8b5e9'
down_revision = '3e44ae42fad8'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('user', 'activation_key',
               existing_type=sa.VARCHAR(),
               nullable=True)
    op.alter_column('user', 'key_expires',
               existing_type=postgresql.TIMESTAMP(),
               nullable=True)
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('user', 'key_expires',
               existing_type=postgresql.TIMESTAMP(),
               nullable=False)
    op.alter_column('user', 'activation_key',
               existing_type=sa.VARCHAR(),
               nullable=False)
    # ### end Alembic commands ###