"""empty message

Revision ID: 2ec1bca57907
Revises: 40f81e25e885
Create Date: 2020-11-07 08:58:11.514284

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '2ec1bca57907'
down_revision = '40f81e25e885'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('tblpricelistrow', sa.Column('item_code', sa.String(length=100), nullable=False))
    op.create_foreign_key(None, 'tblpricelistrow', 'tblitems', ['item_code'], ['item_code'], ondelete='NO ACTION')
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint(None, 'tblpricelistrow', type_='foreignkey')
    op.drop_column('tblpricelistrow', 'item_code')
    # ### end Alembic commands ###
