"""Property model for TIB (Taxe sur les Immeubles Bâtis)"""
from extensions.db import db
from datetime import datetime
from enum import Enum

class PropertyStatus(Enum):
    DECLARED = "declared"
    VERIFIED = "verified"
    DISPUTED = "disputed"
    RESOLVED = "resolved"

class PropertyAffectation(Enum):
    RESIDENTIAL = "residential"
    COMMERCIAL = "commercial"
    INDUSTRIAL = "industrial"
    AGRICULTURAL = "agricultural"
    ADMINISTRATIVE = "administrative"

class Property(db.Model):
    __tablename__ = 'properties'
    __table_args__ = (
        db.UniqueConstraint('owner_id', 'street_address', 'city', 'commune_id', 
                           name='unique_property_per_owner_commune'),
    )
    
    id = db.Column(db.Integer, primary_key=True)
    owner_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # NEW: Municipality association (required)
    commune_id = db.Column(db.Integer, db.ForeignKey('commune.id'), nullable=False)
    
    # Location (Article 1 - Définitions)
    street_address = db.Column(db.String(255), nullable=False)
    city = db.Column(db.String(120), nullable=False)
    delegation = db.Column(db.String(120))  # Tunisia administrative division
    post_code = db.Column(db.String(10))
    
    # GPS Coordinates
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)
    
    # Property Details
    surface_couverte = db.Column(db.Float, nullable=False)  # Built surface in m²
    surface_totale = db.Column(db.Float)  # Total surface
    affectation = db.Column(db.Enum(PropertyAffectation), nullable=False)
    
    # Composition
    nb_floors = db.Column(db.Integer)
    nb_rooms = db.Column(db.Integer)
    construction_year = db.Column(db.Integer)
    
    # Tax details
    # CHANGED: reference_price → reference_price_per_m2 (per square meter, not total)
    reference_price_per_m2 = db.Column(db.Float)  # Prix de référence from Article 4 (TND/m²)
    tax_rate_category = db.Column(db.Integer)  # Surface category (Article 4)
    service_rate = db.Column(db.Integer)  # Number of services (Article 5: 8%, 10%, 12%, 14%)
    
    # Status
    status = db.Column(db.Enum(PropertyStatus), default=PropertyStatus.DECLARED)
    is_exempt = db.Column(db.Boolean, default=False)  # Article 5 exemptions
    exemption_reason = db.Column(db.String(255))
    
    # Satellite verification
    satellite_verified = db.Column(db.Boolean, default=False)
    satellite_verification_date = db.Column(db.DateTime)
    satellite_notes = db.Column(db.Text)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    commune = db.relationship('Commune', back_populates='properties')
    taxes = db.relationship('Tax', backref='property', lazy=True, cascade='all, delete-orphan')
    inspections = db.relationship('Inspection', backref='property', lazy=True, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Property {self.id} - {self.street_address}>'
