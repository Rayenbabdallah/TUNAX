"""Payment Plan model"""
from extensions.db import db
from datetime import datetime
from enum import Enum

class PaymentPlanStatus(Enum):
    PENDING = "pending"
    APPROVED = "approved"
    ACTIVE = "active"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

class PaymentPlan(db.Model):
    __tablename__ = 'payment_plans'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    tax_id = db.Column(db.Integer, db.ForeignKey('taxes.id'), nullable=False)
    total_amount = db.Column(db.Float, nullable=False)
    num_installments = db.Column(db.Integer, nullable=False)
    installment_amount = db.Column(db.Float, nullable=False)
    paid_installments = db.Column(db.Integer, default=0)
    status = db.Column(db.Enum(PaymentPlanStatus), default=PaymentPlanStatus.PENDING)
    requested_date = db.Column(db.DateTime, default=datetime.utcnow)
    last_payment_date = db.Column(db.DateTime)
    
    # Relationships
    user = db.relationship('User', backref='payment_plans')
    tax = db.relationship('Tax', backref='payment_plans')
