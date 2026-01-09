"""Commune (municipality) model"""
from extensions.db import db
from datetime import datetime


class Commune(db.Model):
    """Municipality entity from communes_tn.csv"""
    id = db.Column(db.Integer, primary_key=True)
    code_municipalite = db.Column(db.String(10), unique=True, nullable=False)
    nom_municipalite_fr = db.Column(db.String(255), nullable=False)
    code_gouvernorat = db.Column(db.String(10))
    nom_gouvernorat_fr = db.Column(db.String(255))
    type_mun_fr = db.Column(db.String(50))
    
    # Relationships
    reference_prices = db.relationship('MunicipalReferencePrice', back_populates='commune', cascade='all, delete-orphan')
    service_configs = db.relationship('MunicipalServiceConfig', back_populates='commune', cascade='all, delete-orphan')
    document_requirements = db.relationship('DocumentRequirement', back_populates='commune', cascade='all, delete-orphan')
    users = db.relationship('User', back_populates='commune')
    properties = db.relationship('Property', back_populates='commune')
    lands = db.relationship('Land', back_populates='commune')
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<Commune {self.nom_municipalite_fr} ({self.code_municipalite})>"
