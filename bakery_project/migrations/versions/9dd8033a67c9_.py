"""empty message

Revision ID: 9dd8033a67c9
Revises: 52868edd16fd
Create Date: 2020-11-21 09:44:52.862791

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mssql

# revision identifiers, used by Alembic.
revision = '9dd8033a67c9'
down_revision = '52868edd16fd'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('tblfinalcount', sa.Column('auditor_user', sa.String(length=100), nullable=True))
    op.add_column('tblfinalcount', sa.Column('manager_user', sa.String(length=100), nullable=True))
    op.add_column('tblfinalcount', sa.Column('sales_user', sa.String(length=100), nullable=True))
    op.add_column('tblitemreq', sa.Column('isconfirm', sa.Boolean(), nullable=True))
    op.add_column('tblitemreq', sa.Column('isdeliver', sa.Boolean(), nullable=True))
    op.drop_column('tblitemreq', 'confirm')
    op.add_column('tblitemreqrow', sa.Column('deliverqty', sa.Float(), nullable=False))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('tblitemreqrow', 'deliverqty')
    op.add_column('tblitemreq', sa.Column('confirm', mssql.BIT(), autoincrement=False, nullable=True))
    op.drop_column('tblitemreq', 'isdeliver')
    op.drop_column('tblitemreq', 'isconfirm')
    op.drop_column('tblfinalcount', 'sales_user')
    op.drop_column('tblfinalcount', 'manager_user')
    op.drop_column('tblfinalcount', 'auditor_user')
    # ### end Alembic commands ###