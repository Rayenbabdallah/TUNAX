"""Declaration model representing a tax declaration record."""
from datetime import datetime
from enum import Enum
from extensions.db import db


class DeclarationType(Enum):
    """Supported declaration types (extensible)."""
    PROPERTY = "property"
    LAND = "land"
    BUSINESS = "business"
    OTHER = "other"


class Declaration(db.Model):
    __tablename__ = "declarations"

    id = db.Column(db.Integer, primary_key=True)
    owner_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    commune_id = db.Column(db.Integer, db.ForeignKey("commune.id"), nullable=False)
    declaration_type = db.Column(db.String(50), nullable=False)
    reference_id = db.Column(db.Integer)  # optional link to property/land/business record
    status = db.Column(db.String(30), default="submitted")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    owner = db.relationship("User", backref="declarations")
    commune = db.relationship("Commune", backref="declarations")
    documents = db.relationship(
        "Document",
        back_populates="declaration",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
