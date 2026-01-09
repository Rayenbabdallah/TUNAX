"""Tax model for TIB and TTNB calculations"""
from extensions.db import db
from datetime import datetime
from enum import Enum

class TaxType(Enum):
    TIB = "tib"  # Taxe sur les Immeubles Bâtis
    TTNB = "ttnb"  # Taxe sur les Terrains Non Bâtis

class TaxStatus(Enum):
    PENDING = "pending"
    CALCULATED = "calculated"
    NOTIFIED = "notified"
    PAID = "paid"
    OVERDUE = "overdue"
    DISPUTED = "disputed"

class Tax(db.Model):
    __tablename__ = 'taxes'
    __table_args__ = (
        db.UniqueConstraint('property_id', 'tax_year', name='unique_property_tax_per_year'),
        db.UniqueConstraint('land_id', 'tax_year', name='unique_land_tax_per_year'),
    )
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Property or Land reference
    property_id = db.Column(db.Integer, db.ForeignKey('properties.id'), nullable=True)
    land_id = db.Column(db.Integer, db.ForeignKey('lands.id'), nullable=True)
    
    # Tax type
    tax_type = db.Column(db.Enum(TaxType), nullable=False)
    
    # Tax year
    tax_year = db.Column(db.Integer, nullable=False)
    
    # Calculation details (Articles 1-34)
    # For TIB: Article 4 (2% * reference price * surface category)
    # Article 5: Rate based on services (8%, 10%, 12%, 14%)
    base_amount = db.Column(db.Float, nullable=False)  # Base calculation
    rate_percent = db.Column(db.Float, nullable=False)  # Applied rate
    tax_amount = db.Column(db.Float, nullable=False)  # Final tax amount
    
    # Penalties (Article 19)
    penalty_amount = db.Column(db.Float, default=0)
    penalty_reason = db.Column(db.String(255))
    
    # Total due
    total_amount = db.Column(db.Float, nullable=False)
    
    # Status
    status = db.Column(db.Enum(TaxStatus), default=TaxStatus.CALCULATED)
    
    # Notification (Article 8)
    notification_date = db.Column(db.DateTime)
    notification_method = db.Column(db.String(50))  # email, sms, postal
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    payments = db.relationship('Payment', backref='tax', lazy=True, cascade='all, delete-orphan')
    penalties = db.relationship('Penalty', backref='tax', lazy=True, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Tax {self.id} - {self.tax_type.value} {self.tax_year}>'
