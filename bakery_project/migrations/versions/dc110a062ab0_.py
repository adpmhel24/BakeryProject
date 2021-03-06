"""empty message

Revision ID: dc110a062ab0
Revises: e89d1e601734
Create Date: 2020-11-16 13:47:24.519587

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'dc110a062ab0'
down_revision = 'e89d1e601734'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('tblsales', sa.Column('longitude', sa.Float(), nullable=True))
    op.add_column('tblsales', sa.Column('series', sa.Integer(), nullable=True))
    op.create_foreign_key(None, 'tblsales', 'tblseries', ['series'], ['id'], onupdate='NO ACTION', ondelete='NO ACTION')
    op.drop_column('tblsales', 'longtitude')
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('tblsales', sa.Column('longtitude', sa.FLOAT(precision=53), autoincrement=False, nullable=True))
    op.drop_constraint(None, 'tblsales', type_='foreignkey')
    op.drop_column('tblsales', 'series')
    op.drop_column('tblsales', 'longitude')
    # ### end Alembic commands ###
