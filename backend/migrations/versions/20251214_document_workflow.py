"""Add declaration and document workflow tables"""
from alembic import op
import sqlalchemy as sa


revision = "20251214_document_workflow"
down_revision = "6fe70d917932"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    def table_exists(name: str) -> bool:
        return name in inspector.get_table_names()

    def index_exists(table: str, index_name: str) -> bool:
        return any(idx.get("name") == index_name for idx in inspector.get_indexes(table))

    document_status = sa.Enum("PENDING", "APPROVED", "REJECTED", name="documentstatus")

    if not table_exists("declarations"):
        op.create_table(
            "declarations",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("owner_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("commune_id", sa.Integer(), sa.ForeignKey("commune.id"), nullable=False),
            sa.Column("declaration_type", sa.String(length=50), nullable=False),
            sa.Column("reference_id", sa.Integer()),
            sa.Column("status", sa.String(length=30), nullable=False, server_default="submitted"),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
        )

    if not table_exists("document_types"):
        op.create_table(
            "document_types",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("code", sa.String(length=80), nullable=False),
            sa.Column("label", sa.String(length=120), nullable=False),
            sa.Column("description", sa.Text()),
            sa.Column("is_required", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("commune_id", sa.Integer(), sa.ForeignKey("commune.id"), nullable=False),
            sa.Column("created_by", sa.Integer(), sa.ForeignKey("users.id")),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
            sa.UniqueConstraint("commune_id", "code", name="uq_document_types_commune_code"),
        )

    if not table_exists("documents"):
        op.create_table(
            "documents",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("declaration_id", sa.Integer(), sa.ForeignKey("declarations.id"), nullable=False),
            sa.Column("document_type_id", sa.Integer(), sa.ForeignKey("document_types.id"), nullable=False),
            sa.Column("uploader_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("storage_path", sa.String(length=255), nullable=False),
            sa.Column("file_name", sa.String(length=255), nullable=False),
            sa.Column("mime_type", sa.String(length=50), nullable=False),
            sa.Column("file_size", sa.Integer(), nullable=False),
            sa.Column("issue_date", sa.Date()),
            sa.Column("status", document_status, nullable=False, server_default="PENDING"),
            sa.Column("review_comment", sa.Text()),
            sa.Column("review_date", sa.DateTime()),
            sa.Column("reviewed_by", sa.Integer(), sa.ForeignKey("users.id")),
            sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("previous_version_id", sa.Integer(), sa.ForeignKey("documents.id")),
            sa.Column("uploaded_at", sa.DateTime(), server_default=sa.func.now()),
            sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.false()),
        )

    if table_exists("documents") and not index_exists("documents", "ix_documents_declaration_id"):
        op.create_index("ix_documents_declaration_id", "documents", ["declaration_id"])
    if table_exists("documents") and not index_exists("documents", "ix_documents_type_status"):
        op.create_index("ix_documents_type_status", "documents", ["document_type_id", "status"])


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    def table_exists(name: str) -> bool:
        return name in inspector.get_table_names()

    def index_exists(table: str, index_name: str) -> bool:
        return any(idx.get("name") == index_name for idx in inspector.get_indexes(table))

    if table_exists("documents") and index_exists("documents", "ix_documents_type_status"):
        op.drop_index("ix_documents_type_status", table_name="documents")
    if table_exists("documents") and index_exists("documents", "ix_documents_declaration_id"):
        op.drop_index("ix_documents_declaration_id", table_name="documents")
    if table_exists("documents"):
        op.drop_table("documents")
    if table_exists("document_types"):
        op.drop_table("document_types")
    if table_exists("declarations"):
        op.drop_table("declarations")
    op.execute("DROP TYPE IF EXISTS documentstatus")
