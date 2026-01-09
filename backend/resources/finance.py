"""Finance Officer routes"""
from flask import jsonify, request
from flask_smorest import Blueprint
from flask_jwt_extended import jwt_required
from utils.jwt_helpers import get_current_user_id
from extensions.db import db
from models.user import User, UserRole
from models.tax import Tax, TaxStatus
from models.payment import Payment, PaymentStatus
from utils.role_required import finance_required
from utils.validators import ErrorMessages
from datetime import datetime
from marshmallow import Schema, fields
import secrets
from utils.calculator import TaxCalculator

blp = Blueprint('finance', 'finance', url_prefix='/api/v1/finance')
finance_bp = blp


class AttestationSchema(Schema):
    """Schema for payment attestation"""
    start_date = fields.Str(allow_none=True)
    end_date = fields.Str(allow_none=True)


@blp.get('/debtors')
@blp.response(200)
@jwt_required()
@finance_required
def get_debtors():
    """Get list of users with unpaid taxes"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    
    # Get unpaid taxes
    unpaid_taxes = Tax.query.filter(
        Tax.status.in_([TaxStatus.CALCULATED, TaxStatus.NOTIFIED, TaxStatus.DISPUTED])
    ).all()
    # Refresh penalties dynamically
    any_updates = False
    for tax in unpaid_taxes:
        section = 'TIB' if getattr(tax.tax_type, 'name', 'TIB') == 'TIB' else 'TTNB'
        new_penalty = TaxCalculator.compute_late_payment_penalty_for_year(
            tax_amount=tax.tax_amount,
            tax_year=tax.tax_year,
            section=section
        )
        if (tax.penalty_amount or 0.0) != new_penalty or (tax.total_amount or 0.0) != (tax.tax_amount + new_penalty):
            tax.penalty_amount = new_penalty
            tax.total_amount = tax.tax_amount + new_penalty
            any_updates = True
    if any_updates:
        db.session.commit()
    
    # Get unique debtors
    debtors = {}
    for tax in unpaid_taxes:
        if tax.property:
            user_id = tax.property.owner_id
        elif tax.land:
            user_id = tax.land.owner_id
        else:
            continue
        
        if user_id not in debtors:
            debtors[user_id] = {'amount': 0, 'tax_count': 0}
        
        debtors[user_id]['amount'] += tax.total_amount
        debtors[user_id]['tax_count'] += 1
    
    # Get user details
    result = []
    for user_id, debts in debtors.items():
        user = User.query.get(user_id)
        if user:
            result.append({
                'user_id': user_id,
                'username': user.username,
                'email': user.email,
                'unpaid_amount': round(debts['amount'], 2),
                'tax_count': debts['tax_count']
            })
    
    return jsonify({
        'total_debtors': len(result),
        'debtors': sorted(result, key=lambda x: x['unpaid_amount'], reverse=True)
    }), 200

@blp.post('/attestation/<int:user_id>')
@blp.arguments(AttestationSchema, location="json")
@blp.response(200)
@jwt_required()
@finance_required
def issue_attestation(data, user_id):
    """Issue payment attestation"""
    user = User.query.get(user_id)
    
    if not user:
        return jsonify({'error': ErrorMessages.NOT_FOUND}), 404
    
    # Check unpaid taxes
    taxes = Tax.query.filter(
        (Tax.property.has(owner_id=user_id)) | 
        (Tax.land.has(owner_id=user_id))
    ).all()
    # Refresh penalties for user taxes
    any_updates = False
    for t in taxes:
        if t.status != TaxStatus.PAID:
            section = 'TIB' if getattr(t.tax_type, 'name', 'TIB') == 'TIB' else 'TTNB'
            new_penalty = TaxCalculator.compute_late_payment_penalty_for_year(
                tax_amount=t.tax_amount,
                tax_year=t.tax_year,
                section=section
            )
            if (t.penalty_amount or 0.0) != new_penalty or (t.total_amount or 0.0) != (t.tax_amount + new_penalty):
                t.penalty_amount = new_penalty
                t.total_amount = t.tax_amount + new_penalty
                any_updates = True
    if any_updates:
        db.session.commit()

    unpaid = [t for t in taxes if t.status != TaxStatus.PAID]
    
    if unpaid:
        return jsonify({
            'error': ErrorMessages.UNPAID_TAXES,
            'unpaid_count': len(unpaid),
            'total_due': sum(t.total_amount for t in unpaid)
        }), 400
    
    # Generate attestation
    attestation_number = f"ATT-{datetime.utcnow().year}-{secrets.token_hex(6).upper()}"
    
    return jsonify({
        'attestation_number': attestation_number,
        'user_id': user_id,
        'username': user.username,
        'issued_date': datetime.utcnow().isoformat(),
        'issued_by_user_id': get_current_user_id(),
        'message': 'All tax obligations have been paid',
        'validity': '1 year'
    }), 201

@blp.get('/payment-receipts/<int:user_id>')
@blp.response(200)
@jwt_required()
@finance_required
def get_payment_receipts(user_id):
    """Get payment receipts for user"""
    user = User.query.get(user_id)
    
    if not user:
        return jsonify({'error': ErrorMessages.NOT_FOUND}), 404
    
    payments = Payment.query.filter_by(user_id=user_id).all()
    
    return jsonify({
        'user_id': user_id,
        'username': user.username,
        'total_payments': len(payments),
        'total_amount': sum(p.amount for p in payments),
        'payments': [{
            'id': p.id,
            'tax_id': p.tax_id,
            'amount': p.amount,
            'method': p.method.value,
            'reference_number': p.reference_number,
            'payment_date': p.payment_date.isoformat() if p.payment_date else None
        } for p in payments]
    }), 200

@blp.get('/revenue-report')
@blp.response(200)
@jwt_required()
@finance_required
def get_revenue_report():
    """Get revenue report"""
    year = request.args.get('year', datetime.now().year, type=int)
    
    payments = Payment.query.filter_by(status=PaymentStatus.COMPLETED).all()
    
    # Filter by year if needed
    payments = [p for p in payments if p.payment_date and p.payment_date.year == year]
    
    total_revenue = sum(p.amount for p in payments)
    
    # Group by month
    monthly = {}
    for payment in payments:
        month = payment.payment_date.month
        if month not in monthly:
            monthly[month] = 0
        monthly[month] += payment.amount
    
    return jsonify({
        'year': year,
        'total_revenue': round(total_revenue, 2),
        'payment_count': len(payments),
        'monthly_breakdown': {month: round(amount, 2) for month, amount in monthly.items()}
    }), 200
