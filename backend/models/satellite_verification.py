"""Satellite verification records for inspector imagery assessments"""
from extensions.db import db
from datetime import datetime

class SatelliteVerification(db.Model):
    __tablename__ = 'satellite_verification'

    id = db.Column(db.String(36), primary_key=True)
    inspector_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    property_id = db.Column(db.Integer, db.ForeignKey('properties.id'), nullable=True)
    land_id = db.Column(db.Integer, db.ForeignKey('lands.id'), nullable=True)

    satellite_image_url = db.Column(db.Text)
    image_source = db.Column(db.String(50))
    verification_status = db.Column(db.String(50), nullable=False)
    discrepancy_severity = db.Column(db.String(50))
    discrepancy_notes = db.Column(db.Text)
    has_photo_evidence = db.Column(db.Boolean, default=False)

    verified_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'inspector_id': self.inspector_id,
            'property_id': self.property_id,
            'land_id': self.land_id,
            'satellite_image_url': self.satellite_image_url,
            'image_source': self.image_source,
            'verification_status': self.verification_status,
            'discrepancy_severity': self.discrepancy_severity,
            'discrepancy_notes': self.discrepancy_notes,
            'has_photo_evidence': bool(self.has_photo_evidence),
            'verified_at': self.verified_at.isoformat() if self.verified_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
