"""User model for all 8 roles"""
from extensions.db import db
from datetime import datetime
from enum import Enum
import secrets

class UserRole(Enum):
    # Ministry level (nation-wide)
    MINISTRY_ADMIN = "MINISTRY_ADMIN"
    
    # Municipal level (per commune)
    MUNICIPAL_ADMIN = "MUNICIPAL_ADMIN"
    MUNICIPAL_AGENT = "MUNICIPAL_AGENT"
    INSPECTOR = "INSPECTOR"
    FINANCE_OFFICER = "FINANCE_OFFICER"
    CONTENTIEUX_OFFICER = "CONTENTIEUX_OFFICER"
    URBANISM_OFFICER = "URBANISM_OFFICER"
    
    # User level (citizens/businesses)
    CITIZEN = "CITIZEN"
    BUSINESS = "BUSINESS"

class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.Enum(UserRole), nullable=False)
    
    # Municipality association (CONDITIONAL based on role)
    # MINISTRY_ADMIN: null (nation-wide access)
    # MUNICIPAL_ADMIN: required (manages single municipality)
    # Staff (AGENT/INSPECTOR/etc): required (works in single municipality)
    # CITIZEN/BUSINESS: null (can own properties/lands in multiple communes)
    commune_id = db.Column(db.Integer, db.ForeignKey('commune.id'))
    
    # Personal info
    first_name = db.Column(db.String(120))
    last_name = db.Column(db.String(120))
    phone = db.Column(db.String(20))
    cin = db.Column(db.String(30), unique=True)  # National ID
    
    # Business-specific
    business_name = db.Column(db.String(255))
    business_registration = db.Column(db.String(50))
    
    # Status
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    commune = db.relationship('Commune', back_populates='users')
    properties = db.relationship('Property', backref='owner', lazy=True, cascade='all, delete-orphan')
    lands = db.relationship('Land', backref='owner', lazy=True, cascade='all, delete-orphan')
    payments = db.relationship('Payment', backref='user', lazy=True, cascade='all, delete-orphan')
    disputes = db.relationship('Dispute', backref='claimant', lazy=True, foreign_keys='Dispute.claimant_id')
    inspections = db.relationship('Inspection', backref='inspector', lazy=True)
    
    def set_password(self, password):
        """Hash and set password"""
        from werkzeug.security import generate_password_hash
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """Verify password"""
        from werkzeug.security import check_password_hash
        return check_password_hash(self.password_hash, password)
    
    def __repr__(self):
        return f'<User {self.username}>'
