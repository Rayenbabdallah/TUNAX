
"""initial"""

revision = '6fe70d917932'
down_revision = None
branch_labels = None
depends_on = None

from alembic import op
from extensions.db import db

# Import models to register tables on metadata
from models import *  # noqa: F401,F403


def upgrade():
    bind = op.get_bind()
    db.metadata.create_all(bind=bind)


def downgrade():
    bind = op.get_bind()
    db.metadata.drop_all(bind=bind)
