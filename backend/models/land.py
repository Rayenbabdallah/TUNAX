"""Land model for TTNB (Taxe sur les Terrains Non Bâtis)"""
from extensions.db import db
from datetime import datetime
from enum import Enum

class LandStatus(Enum):
    DECLARED = "declared"
    VERIFIED = "verified"
    DISPUTED = "disputed"
    RESOLVED = "resolved"

class LandType(Enum):
    AGRICULTURAL = "agricultural"
    COMMERCIAL = "commercial"
    INDUSTRIAL = "industrial"
    BUILDABLE = "buildable"
    OTHER = "other"

class Land(db.Model):
    __tablename__ = 'lands'
    __table_args__ = (
        db.UniqueConstraint('owner_id', 'street_address', 'city', 'commune_id',
                           name='unique_land_per_owner_commune'),
    )
    
    id = db.Column(db.Integer, primary_key=True)
    owner_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # NEW: Municipality association (required)
    commune_id = db.Column(db.Integer, db.ForeignKey('commune.id'), nullable=False)
    
    # Location
    street_address = db.Column(db.String(255), nullable=False)
    city = db.Column(db.String(120), nullable=False)
    delegation = db.Column(db.String(120))
    post_code = db.Column(db.String(10))
    
    # GPS Coordinates
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)
    
    # Land Details
    surface = db.Column(db.Float, nullable=False)  # Surface in m²
    land_type = db.Column(db.Enum(LandType), nullable=False)
    
    # NEW: Urban zone classification (REQUIRED for TTNB calculation per Décret 2017-396)
    # Values: "haute_densite", "densite_moyenne", "faible_densite", "peripherique"
    urban_zone = db.Column(db.String(50))  # MUST BE SET for TTNB calculation
    
    # Tax details (Article 33: removed old market value logic)
    # DEPRECATED: vénale_value and tariff_value are removed - use urban_zone instead
    vénale_value = db.Column(db.Float)  # DEPRECATED - kept for backward compatibility only
    tariff_value = db.Column(db.Float)  # DEPRECATED - kept for backward compatibility only
    
    # Exemptions (Article 32)
    is_exempt = db.Column(db.Boolean, default=False)
    exemption_reason = db.Column(db.String(255))
    
    # Status
    status = db.Column(db.Enum(LandStatus), default=LandStatus.DECLARED)
    
    # Satellite verification
    satellite_verified = db.Column(db.Boolean, default=False)
    satellite_verification_date = db.Column(db.DateTime)
    satellite_notes = db.Column(db.Text)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    commune = db.relationship('Commune', back_populates='lands')
    taxes = db.relationship('Tax', backref='land', lazy=True, cascade='all, delete-orphan')
    inspections = db.relationship('Inspection', backref='land', lazy=True, cascade='all, delete-orphan')
    
    # Legacy compatibility property
    @property
    def cadastral_reference(self):
        """Alias for urban_zone (legacy field name)"""
        return self.urban_zone
    
    def __repr__(self):
        return f'<Land {self.id} - {self.street_address}>'
