"""empty message

Revision ID: fae78f8156e6
Revises: 8ea92b96c579
Create Date: 2020-11-13 10:17:43.762051

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'fae78f8156e6'
down_revision = '8ea92b96c579'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('tblcounting_inv_row', sa.Column('uom', sa.String(length=50), nullable=True))
    op.create_foreign_key(None, 'tblcounting_inv_row', 'tbluom', ['uom'], ['code'])
    op.add_column('tblitemadjinrow', sa.Column('uom', sa.String(length=50), nullable=False))
    op.add_column('tblitemadjinrow', sa.Column('whsecode', sa.String(length=100), nullable=False))
    op.drop_constraint('FK__tblitemadj__whse__79E80B25', 'tblitemadjinrow', type_='foreignkey')
    op.create_foreign_key(None, 'tblitemadjinrow', 'tbluom', ['uom'], ['code'])
    op.create_foreign_key(None, 'tblitemadjinrow', 'tblwhses', ['whsecode'], ['whsecode'])
    op.drop_column('tblitemadjinrow', 'whse')
    op.add_column('tblitemadjoutrow', sa.Column('uom', sa.String(length=50), nullable=False))
    op.create_foreign_key(None, 'tblitemadjoutrow', 'tbluom', ['uom'], ['code'])
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint(None, 'tblitemadjoutrow', type_='foreignkey')
    op.drop_column('tblitemadjoutrow', 'uom')
    op.add_column('tblitemadjinrow', sa.Column('whse', sa.VARCHAR(length=100, collation='SQL_Latin1_General_CP850_CI_AS'), autoincrement=False, nullable=False))
    op.drop_constraint(None, 'tblitemadjinrow', type_='foreignkey')
    op.drop_constraint(None, 'tblitemadjinrow', type_='foreignkey')
    op.create_foreign_key('FK__tblitemadj__whse__79E80B25', 'tblitemadjinrow', 'tblwhses', ['whse'], ['whsecode'])
    op.drop_column('tblitemadjinrow', 'whsecode')
    op.drop_column('tblitemadjinrow', 'uom')
    op.drop_constraint(None, 'tblcounting_inv_row', type_='foreignkey')
    op.drop_column('tblcounting_inv_row', 'uom')
    # ### end Alembic commands ###
