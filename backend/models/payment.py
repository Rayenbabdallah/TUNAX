"""Payment model"""
from extensions.db import db
from datetime import datetime
from enum import Enum

class PaymentStatus(Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    REFUNDED = "refunded"

class PaymentMethod(Enum):
    CARD = "card"
    BANK_TRANSFER = "bank_transfer"
    CHECK = "check"
    CASH = "cash"

class Payment(db.Model):
    __tablename__ = 'payments'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    tax_id = db.Column(db.Integer, db.ForeignKey('taxes.id'), nullable=False)
    
    # Payment details
    amount = db.Column(db.Float, nullable=False)
    method = db.Column(db.Enum(PaymentMethod), nullable=False)
    status = db.Column(db.Enum(PaymentStatus), default=PaymentStatus.COMPLETED)
    
    # Reference
    reference_number = db.Column(db.String(100), unique=True)
    
    # Attestation
    attestation_issued = db.Column(db.Boolean, default=False)
    attestation_date = db.Column(db.DateTime)
    attestation_number = db.Column(db.String(100))
    
    # Timestamps
    payment_date = db.Column(db.DateTime, default=datetime.utcnow)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<Payment {self.id} - {self.amount} TND>'
