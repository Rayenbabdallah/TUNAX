"""Payment Plan and Installment routes"""
from flask import jsonify, request
from flask_smorest import Blueprint
from flask_jwt_extended import jwt_required
from utils.jwt_helpers import get_current_user_id
from extensions.db import db
from models.payment import Payment, PaymentMethod, PaymentStatus
from models.payment_plan import PaymentPlan, PaymentPlanStatus
from models.tax import Tax, TaxStatus
from utils.role_required import citizen_or_business_required, finance_required
from utils.validators import ErrorMessages
from datetime import datetime, timedelta
from math import ceil
from marshmallow import Schema, fields

blp = Blueprint('payment_plans', 'payment_plans', url_prefix='/api/v1/payment-plans')
payment_plans_bp = blp


class PaymentPlanRequestSchema(Schema):
    """Schema for payment plan requests"""
    tax_id = fields.Int(required=True)
    num_installments = fields.Int(required=True)


class PaymentInstallmentSchema(Schema):
    """Schema for installment payments"""
    method = fields.Str(allow_none=True, missing='bank_transfer')


@blp.post('/request')
@blp.arguments(PaymentPlanRequestSchema, location="json")
@blp.response(201)
@jwt_required()
@citizen_or_business_required
def request_payment_plan(data):
    
    if not data.get('tax_id') or not data.get('num_installments'):
        return jsonify({'error': 'tax_id and num_installments required'}), 400
    
    tax = Tax.query.get(data['tax_id'])
    
    if not tax:
        return jsonify({'error': ErrorMessages.NOT_FOUND}), 404
    
    # Verify ownership
    if tax.property and tax.property.owner_id != user_id:
        return jsonify({'error': ErrorMessages.ACCESS_DENIED}), 403
    if tax.land and tax.land.owner_id != user_id:
        return jsonify({'error': ErrorMessages.ACCESS_DENIED}), 403
    
    num_installments = min(data['num_installments'], 12)  # Max 12 months
    installment_amount = round(tax.total_amount / num_installments, 2)
    
    plan = PaymentPlan(
        user_id=user_id,
        tax_id=tax.id,
        total_amount=tax.total_amount,
        num_installments=num_installments,
        installment_amount=installment_amount,
        status=PaymentPlanStatus.PENDING,
        requested_date=datetime.utcnow()
    )
    
    db.session.add(plan)
    db.session.commit()
    
    return jsonify({
        'message': 'Payment plan requested',
        'plan_id': plan.id,
        'total_amount': plan.total_amount,
        'num_installments': num_installments,
        'installment_amount': installment_amount,
        'status': plan.status.value
    }), 201

@blp.get('/active')
@blp.response(200)
@jwt_required()
@citizen_or_business_required
def get_active_payment_plans():
    """Get active payment plans"""
    user_id = get_current_user_id()
    
    plans = PaymentPlan.query.filter_by(user_id=user_id).filter(
        PaymentPlan.status.in_([PaymentPlanStatus.APPROVED, PaymentPlanStatus.ACTIVE])
    ).all()
    
    return jsonify({
        'total': len(plans),
        'plans': [{
            'id': p.id,
            'tax_id': p.tax_id,
            'total_amount': p.total_amount,
            'num_installments': p.num_installments,
            'paid_installments': p.paid_installments,
            'remaining_amount': p.total_amount - (p.paid_installments * p.installment_amount),
            'status': p.status.value,
            'requested_date': p.requested_date.isoformat() if p.requested_date else None
        } for p in plans]
    }), 200

@blp.post('/<int:plan_id>/pay-installment')
@blp.arguments(PaymentInstallmentSchema, location="json")
@blp.response(200)
@jwt_required()
@citizen_or_business_required
def pay_installment(data, plan_id):
    
    plan = PaymentPlan.query.get(plan_id)
    
    if not plan:
        return jsonify({'error': ErrorMessages.NOT_FOUND}), 404
    
    if plan.user_id != user_id:
        return jsonify({'error': ErrorMessages.ACCESS_DENIED}), 403
    
    if plan.status not in [PaymentPlanStatus.APPROVED, PaymentPlanStatus.ACTIVE]:
        return jsonify({'error': 'Payment plan is not active'}), 400
    
    if plan.paid_installments >= plan.num_installments:
        return jsonify({'error': 'All installments already paid'}), 400
    
    # Create payment record
    payment = Payment(
        user_id=user_id,
        tax_id=plan.tax_id,
        amount=plan.installment_amount,
        method=data.get('method', 'bank_transfer'),
        status=PaymentStatus.COMPLETED,
        reference_number=f"PLAN-{plan_id}-{plan.paid_installments + 1}"
    )
    
    plan.paid_installments += 1
    plan.last_payment_date = datetime.utcnow()
    
    if plan.paid_installments >= plan.num_installments:
        plan.status = PaymentPlanStatus.COMPLETED
        tax = Tax.query.get(plan.tax_id)
        if tax:
            tax.status = TaxStatus.PAID
    
    db.session.add(payment)
    db.session.commit()
    
    return jsonify({
        'message': 'Installment payment recorded',
        'payment_id': payment.id,
        'installment_num': plan.paid_installments,
        'amount': plan.installment_amount,
        'remaining_installments': plan.num_installments - plan.paid_installments
    }), 200
