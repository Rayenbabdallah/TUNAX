"""Penalty model for non-compliance"""
from extensions.db import db
from datetime import datetime
from enum import Enum

class PenaltyType(Enum):
    LATE_DECLARATION = "late_declaration"  # Article 19
    LATE_PAYMENT = "late_payment"  # Article 19
    FALSE_INFORMATION = "false_information"
    NON_COMPLIANCE = "non_compliance"

class PenaltyStatus(Enum):
    ISSUED = "issued"
    PAID = "paid"
    APPEALED = "appealed"

class Penalty(db.Model):
    __tablename__ = 'penalties'
    
    id = db.Column(db.Integer, primary_key=True)
    tax_id = db.Column(db.Integer, db.ForeignKey('taxes.id'), nullable=False)
    
    # Penalty type (Article 19)
    penalty_type = db.Column(db.Enum(PenaltyType), nullable=False)
    
    # Amount
    amount = db.Column(db.Float, nullable=False)
    percentage = db.Column(db.Float)  # If percentage-based
    
    # Details
    reason = db.Column(db.Text)
    issued_by = db.Column(db.Integer, db.ForeignKey('users.id'))  # Municipal agent
    
    # Status
    status = db.Column(db.Enum(PenaltyStatus), default=PenaltyStatus.ISSUED)
    
    # Deadline
    deadline = db.Column(db.DateTime)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<Penalty {self.id} - {self.penalty_type.value}>'
