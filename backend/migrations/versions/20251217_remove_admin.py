"""
Data migration: convert legacy ADMIN role to MUNICIPAL_ADMIN.
"""

revision = '20251217_remove_admin'
down_revision = '20251215_document_requirements'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text


def upgrade():
    conn = op.get_bind()
    
    # Check if any users have the legacy ADMIN role (using CAST to avoid enum type errors)
    result = conn.execute(text("SELECT COUNT(*) FROM users WHERE role::text = 'ADMIN'"))
    count = result.scalar()
    
    # Only execute the update if ADMIN role exists in the data
    if count > 0:
        conn.execute(text("""
            UPDATE users
            SET role = 'MUNICIPAL_ADMIN'
            WHERE role::text = 'ADMIN'
        """))


def downgrade():
    conn = op.get_bind()
    # Revert back (optional - just leave MUNICIPAL_ADMIN in place)
    pass
