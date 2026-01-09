"""Inspection model for field inspections"""
from extensions.db import db
from datetime import datetime
from enum import Enum

class InspectionStatus(Enum):
    SCHEDULED = "scheduled"
    COMPLETED = "completed"
    FLAGGED = "flagged"

class Inspection(db.Model):
    __tablename__ = 'inspections'
    
    id = db.Column(db.Integer, primary_key=True)
    inspector_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # Property or Land
    property_id = db.Column(db.Integer, db.ForeignKey('properties.id'), nullable=True)
    land_id = db.Column(db.Integer, db.ForeignKey('lands.id'), nullable=True)
    
    # Inspection details
    status = db.Column(db.Enum(InspectionStatus), default=InspectionStatus.SCHEDULED)
    date = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Findings
    notes = db.Column(db.Text)
    satellite_verified = db.Column(db.Boolean, default=False)
    discrepancies_found = db.Column(db.Boolean, default=False)
    
    # Photos/Evidence
    evidence_urls = db.Column(db.JSON)
    
    # Recommendation
    recommendation = db.Column(db.Text)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<Inspection {self.id}>'
