"""Document and document type models."""
from datetime import datetime
from enum import Enum
from extensions.db import db


class DocumentStatus(Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class DocumentType(db.Model):
    """Configurable document types, scoped per municipality."""

    __tablename__ = "document_types"

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(80), nullable=False)
    label = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text)
    is_required = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=True)
    commune_id = db.Column(db.Integer, db.ForeignKey("commune.id"), nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey("users.id"))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    commune = db.relationship("Commune", backref="document_types")
    creator = db.relationship("User", backref="created_document_types")

    __table_args__ = (
        db.UniqueConstraint("commune_id", "code", name="uq_document_types_commune_code"),
    )


class Document(db.Model):
    """Versioned declaration documents with review lifecycle."""

    __tablename__ = "documents"

    id = db.Column(db.Integer, primary_key=True)
    declaration_id = db.Column(db.Integer, db.ForeignKey("declarations.id"), nullable=False)
    document_type_id = db.Column(db.Integer, db.ForeignKey("document_types.id"), nullable=False)
    uploader_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    storage_path = db.Column(db.String(255), nullable=False)
    file_name = db.Column(db.String(255), nullable=False)
    mime_type = db.Column(db.String(50), nullable=False)
    file_size = db.Column(db.Integer, nullable=False)
    issue_date = db.Column(db.Date)
    status = db.Column(db.Enum(DocumentStatus), default=DocumentStatus.PENDING, nullable=False)
    review_comment = db.Column(db.Text)
    review_date = db.Column(db.DateTime)
    reviewed_by = db.Column(db.Integer, db.ForeignKey("users.id"))
    version = db.Column(db.Integer, default=1, nullable=False)
    previous_version_id = db.Column(db.Integer, db.ForeignKey("documents.id"))
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_deleted = db.Column(db.Boolean, default=False)

    declaration = db.relationship("Declaration", back_populates="documents")
    document_type = db.relationship("DocumentType")
    uploader = db.relationship("User", foreign_keys=[uploader_id], backref="uploaded_documents")
    reviewer = db.relationship("User", foreign_keys=[reviewed_by], backref="reviewed_documents")
    previous_version = db.relationship("Document", remote_side=[id], uselist=False)

