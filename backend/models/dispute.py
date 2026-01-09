"""Dispute and Contentieux model for tax disputes"""
from extensions.db import db
from datetime import datetime
from enum import Enum

class DisputeStatus(Enum):
    SUBMITTED = "submitted"  # Article 23
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    COMMISSION_REVIEW = "commission_review"  # Articles 24-26
    APPEALED = "appealed"
    RESOLVED = "resolved"

class DisputeType(Enum):
    EVALUATION = "evaluation"  # Challenge tax evaluation
    CALCULATION = "calculation"  # Challenge calculation
    EXEMPTION = "exemption"  # Exemption claim
    PENALTY = "penalty"  # Challenge penalty

class Dispute(db.Model):
    __tablename__ = 'disputes'
    
    id = db.Column(db.Integer, primary_key=True)
    claimant_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # Dispute details
    dispute_type = db.Column(db.Enum(DisputeType), nullable=False)
    subject = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=False)
    
    # Reference (tax or property)
    tax_id = db.Column(db.Integer, db.ForeignKey('taxes.id'))
    property_id = db.Column(db.Integer, db.ForeignKey('properties.id'))
    
    # Claimed amount (if applicable)
    claimed_amount = db.Column(db.Float)
    
    # Status (Articles 23-26)
    status = db.Column(db.Enum(DisputeStatus), default=DisputeStatus.SUBMITTED)
    
    # Processing
    assigned_to = db.Column(db.Integer, db.ForeignKey('users.id'))  # Contentieux officer
    submission_date = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Commission de révision (Articles 24-26)
    commission_reviewed = db.Column(db.Boolean, default=False)
    commission_review_date = db.Column(db.DateTime)
    commission_decision = db.Column(db.Text)
    
    # Final ruling
    final_decision = db.Column(db.Text)
    final_amount = db.Column(db.Float)
    decision_date = db.Column(db.DateTime)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<Dispute {self.id} - {self.dispute_type.value}>'
