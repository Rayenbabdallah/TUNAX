"""Add locality scope to municipal services

Revision ID: 20251215_locality_services
Revises: 20251215_budget_vote_weights
Create Date: 2025-12-15
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20251215_locality_services'
down_revision = '20251215_budget_vote_weights'
branch_labels = None
depends_on = None


def upgrade():
    # Check if column exists before adding
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [col['name'] for col in inspector.get_columns('municipal_service_config')]
    
    if 'locality_name' not in columns:
        op.add_column('municipal_service_config', sa.Column('locality_name', sa.String(length=255), nullable=True))
    
    # Check if constraint exists before dropping
    constraints = [con['name'] for con in inspector.get_unique_constraints('municipal_service_config')]
    if 'unique_service_per_commune' in constraints:
        op.drop_constraint('unique_service_per_commune', 'municipal_service_config', type_='unique')
    
    # Recreate constraint with locality_name
    op.create_unique_constraint(
        'unique_service_per_commune',
        'municipal_service_config',
        ['commune_id', 'service_code', 'locality_name']
    )


def downgrade():
    op.drop_constraint('unique_service_per_commune', 'municipal_service_config', type_='unique')
    op.create_unique_constraint(
        'unique_service_per_commune',
        'municipal_service_config',
        ['commune_id', 'service_code']
    )
    op.drop_column('municipal_service_config', 'locality_name')
