"""Reclamation model for service complaints"""
from extensions.db import db
from datetime import datetime
from enum import Enum

class ReclamationType(Enum):
    LIGHTING = "lighting"
    ROAD_MAINTENANCE = "road_maintenance"
    DRAINAGE = "drainage"
    WASTE_COLLECTION = "waste_collection"
    WATER = "water"
    OTHER = "other"

class ReclamationStatus(Enum):
    SUBMITTED = "submitted"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    CLOSED = "closed"

class Reclamation(db.Model):
    __tablename__ = 'reclamations'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # Reclamation type
    reclamation_type = db.Column(db.Enum(ReclamationType), nullable=False)
    
    # Location
    street_address = db.Column(db.String(255))
    city = db.Column(db.String(120))
    
    # Details
    description = db.Column(db.Text, nullable=False)
    priority = db.Column(db.String(20))  # low, medium, high
    
    # Status
    status = db.Column(db.Enum(ReclamationStatus), default=ReclamationStatus.SUBMITTED)
    
    # Assignment
    assigned_to = db.Column(db.Integer, db.ForeignKey('users.id'))  # Municipal agent
    
    # Resolution
    resolution = db.Column(db.Text)
    resolved_date = db.Column(db.DateTime)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<Reclamation {self.id}>'
