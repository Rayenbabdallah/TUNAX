"""Audit Log model"""
from extensions.db import db
from datetime import datetime

class AuditLog(db.Model):
    __tablename__ = 'audit_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    entity_type = db.Column(db.String(50), nullable=False)
    entity_id = db.Column(db.Integer, nullable=False)
    action = db.Column(db.String(50), nullable=False)  # create, update, delete
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    changes = db.Column(db.JSON)  # What was changed
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', backref='audit_logs')
    
    __table_args__ = (
        db.Index('idx_entity', 'entity_type', 'entity_id'),
        db.Index('idx_timestamp', 'timestamp'),
    )
