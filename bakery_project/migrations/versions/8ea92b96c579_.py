"""empty message

Revision ID: 8ea92b96c579
Revises: bed8bad98569
Create Date: 2020-11-12 17:01:16.879270

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '8ea92b96c579'
down_revision = 'bed8bad98569'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('tbluser', sa.Column('isChecker', sa.Boolean(), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('tbluser', 'isChecker')
    # ### end Alembic commands ###
