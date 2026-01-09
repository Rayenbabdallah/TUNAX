"""Permit model for construction permits"""
from extensions.db import db
from datetime import datetime
from enum import Enum

class PermitType(Enum):
    CONSTRUCTION = "construction"
    LOTISSEMENT = "lotissement"
    OCCUPANCY = "occupancy"
    SIGNATURE_LEGALIZATION = "signature_legalization"

class PermitStatus(Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    BLOCKED_UNPAID_TAXES = "blocked_unpaid_taxes"

class Permit(db.Model):
    __tablename__ = 'permits'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # Permit details
    permit_type = db.Column(db.Enum(PermitType), nullable=False)
    status = db.Column(db.Enum(PermitStatus), default=PermitStatus.PENDING)
    
    # Property reference
    property_id = db.Column(db.Integer, db.ForeignKey('properties.id'))
    
    # Description
    description = db.Column(db.Text)
    
    # Tax requirement (Article 13)
    taxes_paid = db.Column(db.Boolean, default=False)
    tax_payment_date = db.Column(db.DateTime)
    
    # Processing
    submitted_date = db.Column(db.DateTime, default=datetime.utcnow)
    decision_date = db.Column(db.DateTime)
    decision_by = db.Column(db.Integer, db.ForeignKey('users.id'))  # Urbanism officer
    
    # Notes
    notes = db.Column(db.Text)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<Permit {self.id} - {self.permit_type.value}>'
