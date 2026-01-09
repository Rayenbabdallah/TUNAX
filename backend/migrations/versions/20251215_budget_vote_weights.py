"""Add commune binding and vote weights to participatory budget

Revision ID: 20251215_budget_vote_weights
Revises: 20251214_add_2fa
Create Date: 2025-12-15
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20251215_budget_vote_weights'
down_revision = '20251214_add_2fa'
branch_labels = None
depends_on = None


def upgrade():
    # Check if columns already exist (may have been created by initial migration)
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    
    budget_projects_columns = [col['name'] for col in inspector.get_columns('budget_projects')]
    budget_votes_columns = [col['name'] for col in inspector.get_columns('budget_votes')]
    
    # Link budget projects to a commune (municipality scope)
    if 'commune_id' not in budget_projects_columns:
        op.add_column('budget_projects', sa.Column('commune_id', sa.Integer(), nullable=True))
        op.create_foreign_key(
            'fk_budget_projects_commune',
            'budget_projects',
            'commune',
            ['commune_id'],
            ['id']
        )

    # Track vote weight (number of eligible assets a voter owns)
    if 'weight' not in budget_votes_columns:
        op.add_column(
            'budget_votes',
            sa.Column('weight', sa.Integer(), nullable=False, server_default='1')
        )
        op.alter_column('budget_votes', 'weight', server_default=None)


def downgrade():
    op.drop_constraint('fk_budget_projects_commune', 'budget_projects', type_='foreignkey')
    op.drop_column('budget_projects', 'commune_id')
    op.drop_column('budget_votes', 'weight')
