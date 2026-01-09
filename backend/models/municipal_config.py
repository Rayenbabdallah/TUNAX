"""Municipal configuration models"""
from extensions.db import db
from datetime import datetime
import json


class MunicipalReferencePrice(db.Model):
    """TIB reference prices set by municipal admin per category"""
    id = db.Column(db.Integer, primary_key=True)
    commune_id = db.Column(db.Integer, db.ForeignKey('commune.id'), nullable=False)
    
    # TIB Category (1-4) based on covered surface
    tib_category = db.Column(db.Integer, nullable=False)  # 1, 2, 3, or 4
    
    # Legal bounds from Code de la Fiscalité Locale
    legal_min = db.Column(db.Float, nullable=False)
    legal_max = db.Column(db.Float, nullable=False)
    
    # Municipality's chosen reference price (MUST be within bounds)
    reference_price_per_m2 = db.Column(db.Float, nullable=False)
    
    # Audit trail
    set_by_user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    set_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    commune = db.relationship('Commune', back_populates='reference_prices')
    set_by_user = db.relationship('User', foreign_keys=[set_by_user_id])
    
    __table_args__ = (
        db.UniqueConstraint('commune_id', 'tib_category', name='unique_ref_price_per_commune_category'),
    )
    
    def __repr__(self):
        return f"<RefPrice Cat{self.tib_category} {self.reference_price_per_m2} TND/m²>"


class MunicipalServiceConfig(db.Model):
    """Services available per municipality/locality"""
    id = db.Column(db.Integer, primary_key=True)
    commune_id = db.Column(db.Integer, db.ForeignKey('commune.id'), nullable=False)
    locality_name = db.Column(db.String(255), nullable=True)
    
    # Service definition
    service_name = db.Column(db.String(255), nullable=False)
    service_code = db.Column(db.String(50), nullable=False)
    
    # Availability flag
    is_available = db.Column(db.Boolean, default=True)
    
    # Audit trail
    configured_by_user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    configured_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    commune = db.relationship('Commune', back_populates='service_configs')
    configured_by_user = db.relationship('User', foreign_keys=[configured_by_user_id])
    
    __table_args__ = (
        db.UniqueConstraint('commune_id', 'service_code', 'locality_name', name='unique_service_per_commune'),
    )
    
    def __repr__(self):
        scope = self.locality_name or 'ALL'
        return f"<Service {self.service_code} ({self.service_name}) - {scope}>"


class DocumentRequirement(db.Model):
    """Configurable required documents per municipality and property/land type"""
    id = db.Column(db.Integer, primary_key=True)
    commune_id = db.Column(db.Integer, db.ForeignKey('commune.id'), nullable=False)
    
    # Type of declaration (property, land, or both)
    declaration_type = db.Column(db.String(50), nullable=False)  # 'property', 'land', or 'all'
    
    # Document name and code
    document_name = db.Column(db.String(255), nullable=False)
    document_code = db.Column(db.String(100), nullable=False)
    
    # Description for citizens/businesses
    description = db.Column(db.Text)
    
    # Mandatory flag
    is_mandatory = db.Column(db.Boolean, default=True)
    
    # Display order
    display_order = db.Column(db.Integer, default=0)
    
    # Audit trail
    created_by_user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_by_user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    commune = db.relationship('Commune', back_populates='document_requirements')
    created_by_user = db.relationship('User', foreign_keys=[created_by_user_id])
    updated_by_user = db.relationship('User', foreign_keys=[updated_by_user_id])
    
    __table_args__ = (
        db.UniqueConstraint('commune_id', 'declaration_type', 'document_code', name='unique_doc_requirement_per_commune'),
    )
    
    def __repr__(self):
        return f"<DocReq {self.declaration_type} - {self.document_code}>"
