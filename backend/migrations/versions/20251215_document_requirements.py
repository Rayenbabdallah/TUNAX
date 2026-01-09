"""Add document requirements configuration per municipality

Revision ID: 20251215_document_requirements
Revises: 20251215_locality_services
Create Date: 2025-12-15
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20251215_document_requirements'
down_revision = '20251215_locality_services'
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    # Skip table creation if it already exists (idempotent reruns/seed)
    if 'document_requirement' not in inspector.get_table_names():
        op.create_table(
            'document_requirement',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('commune_id', sa.Integer(), nullable=False),
            sa.Column('declaration_type', sa.String(length=50), nullable=False),
            sa.Column('document_name', sa.String(length=255), nullable=False),
            sa.Column('document_code', sa.String(length=100), nullable=False),
            sa.Column('description', sa.Text(), nullable=True),
            sa.Column('is_mandatory', sa.Boolean(), nullable=False, server_default='true'),
            sa.Column('display_order', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('created_by_user_id', sa.Integer(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column('updated_by_user_id', sa.Integer(), nullable=True),
            sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.ForeignKeyConstraint(['commune_id'], ['commune.id'], ),
            sa.ForeignKeyConstraint(['created_by_user_id'], ['users.id'], ),
            sa.ForeignKeyConstraint(['updated_by_user_id'], ['users.id'], ),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('commune_id', 'declaration_type', 'document_code', name='unique_doc_requirement_per_commune')
        )

    # Ensure indexes exist (create if missing)
    existing_indexes = {idx['name'] for idx in inspector.get_indexes('document_requirement')} if 'document_requirement' in inspector.get_table_names() else set()
    if 'ix_document_requirement_commune_id' not in existing_indexes and 'document_requirement' in inspector.get_table_names():
        op.create_index('ix_document_requirement_commune_id', 'document_requirement', ['commune_id'])
    if 'ix_document_requirement_declaration_type' not in existing_indexes and 'document_requirement' in inspector.get_table_names():
        op.create_index('ix_document_requirement_declaration_type', 'document_requirement', ['declaration_type'])


def downgrade():
    op.drop_index('ix_document_requirement_declaration_type', table_name='document_requirement')
    op.drop_index('ix_document_requirement_commune_id', table_name='document_requirement')
    op.drop_table('document_requirement')
