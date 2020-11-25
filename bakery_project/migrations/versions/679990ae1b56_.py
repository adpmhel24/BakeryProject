"""empty message

Revision ID: 679990ae1b56
Revises: ba446c83b09d
Create Date: 2020-11-12 10:59:16.462641

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '679990ae1b56'
down_revision = 'ba446c83b09d'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('tbluser', sa.Column('isAllowEnding', sa.Boolean(), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('tbluser', 'isAllowEnding')
    # ### end Alembic commands ###
