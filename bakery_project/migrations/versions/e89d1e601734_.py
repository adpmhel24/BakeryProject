"""empty message

Revision ID: e89d1e601734
Revises: ac0fa831685d
Create Date: 2020-11-16 11:42:13.134444

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e89d1e601734'
down_revision = 'ac0fa831685d'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('tblpulloutreq', sa.Column('user_type', sa.String(length=50), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('tblpulloutreq', 'user_type')
    # ### end Alembic commands ###
