"""Exemption model"""
from extensions.db import db
from datetime import datetime
from enum import Enum

class ExemptionStatus(Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    PARTIAL = "partial"

class ExemptionType(Enum):
    FULL = "full"
    REDUCTION = "reduction"
    SPECIAL = "special"

class Exemption(db.Model):
    __tablename__ = 'exemptions'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    exemption_type = db.Column(db.String(50), nullable=False)
    property_id = db.Column(db.Integer, db.ForeignKey('properties.id'))
    land_id = db.Column(db.Integer, db.ForeignKey('lands.id'))
    tax_id = db.Column(db.Integer, db.ForeignKey('taxes.id'))
    reason = db.Column(db.Text, nullable=False)
    supporting_docs = db.Column(db.JSON)
    requested_amount = db.Column(db.Float)
    status = db.Column(db.Enum(ExemptionStatus), default=ExemptionStatus.PENDING)
    decision = db.Column(db.String(50))
    admin_notes = db.Column(db.Text)
    decided_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    requested_date = db.Column(db.DateTime, default=datetime.utcnow)
    decision_date = db.Column(db.DateTime)
    
    # Relationships
    user = db.relationship('User', backref='exemptions', foreign_keys=[user_id])
    decider = db.relationship('User', foreign_keys=[decided_by])
    property = db.relationship('Property', backref='exemptions')
    land = db.relationship('Land', backref='exemptions')
    tax = db.relationship('Tax', backref='exemptions')
