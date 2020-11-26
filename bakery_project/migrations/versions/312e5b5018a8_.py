"""empty message

Revision ID: 312e5b5018a8
Revises: 1198e46086f1
Create Date: 2020-11-24 13:44:27.294418

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '312e5b5018a8'
down_revision = '1198e46086f1'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('tbluser', sa.Column('isAccounting', sa.Boolean(), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('tbluser', 'isAccounting')
    # ### end Alembic commands ###