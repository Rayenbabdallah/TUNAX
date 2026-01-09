"""Add 2FA support

Revision ID: 20251214_add_2fa
Revises: 20251214_document_workflow
Create Date: 2025-12-14

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = '20251214_add_2fa'
down_revision = '20251214_document_workflow'
branch_labels = None
depends_on = None

def upgrade():
    # Check if table already exists (may have been created by initial migration)
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    
    if 'two_factor_auth' not in inspector.get_table_names():
        # Create two_factor_auth table
        op.create_table(
            'two_factor_auth',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('user_id', sa.Integer(), nullable=False),
            sa.Column('secret_key', sa.String(length=32), nullable=False),
            sa.Column('is_enabled', sa.Boolean(), nullable=True, default=False),
            sa.Column('backup_codes', sa.Text(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=True),
            sa.Column('last_used', sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('user_id')
        )
        op.create_index(op.f('ix_two_factor_auth_user_id'), 'two_factor_auth', ['user_id'], unique=True)

def downgrade():
    op.drop_index(op.f('ix_two_factor_auth_user_id'), table_name='two_factor_auth')
    op.drop_table('two_factor_auth')
