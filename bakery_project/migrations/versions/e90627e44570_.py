"""empty message

Revision ID: e90627e44570
Revises: 9dd8033a67c9
Create Date: 2020-11-22 15:40:52.274263

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mssql

# revision identifiers, used by Alembic.
revision = 'e90627e44570'
down_revision = '9dd8033a67c9'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('tblitemreq', sa.Column('confirm', sa.Boolean(), nullable=True))
    op.drop_column('tblitemreq', 'isconfirm')
    op.drop_column('tblitemreq', 'isdeliver')
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('tblitemreq', sa.Column('isdeliver', mssql.BIT(), autoincrement=False, nullable=True))
    op.add_column('tblitemreq', sa.Column('isconfirm', mssql.BIT(), autoincrement=False, nullable=True))
    op.drop_column('tblitemreq', 'confirm')
    # ### end Alembic commands ###
