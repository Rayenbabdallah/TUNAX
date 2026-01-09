"""Permit management routes (flask-smorest)"""
from flask import jsonify, request
from flask_smorest import Blueprint
from flask_jwt_extended import jwt_required
from utils.jwt_helpers import get_current_user_id
from extensions.db import db
from models.user import User, UserRole
from models.permit import Permit, PermitType, PermitStatus
from models.tax import Tax, TaxStatus
from schemas.tax_permit import PermitRequestSchema, PermitSchema, PermitDecisionSchema
from marshmallow import ValidationError
from utils.role_required import citizen_or_business_required, urbanism_required
from utils.validators import ErrorMessages
from utils.calculator import TaxCalculator
from datetime import datetime

blp = Blueprint('permits', 'permits', url_prefix='/api/v1/permits')

@blp.post('/request')
@jwt_required()
@citizen_or_business_required
@blp.arguments(PermitRequestSchema)
@blp.response(201, PermitSchema)
def request_permit(data):
    """Request a permit (Article 13 - requires paid taxes)"""
    user_id = get_current_user_id()
    
    # Check if user has unpaid taxes (Article 13)
    taxes = Tax.query.filter(
        (Tax.property.has(owner_id=user_id)) |
        (Tax.land.has(owner_id=user_id))
    ).all()
    
    # Refresh penalties for user's taxes
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
            'message': 'You must pay all outstanding taxes before requesting permits (Article 13)',
            'unpaid_count': len(unpaid),
            'total_due': sum(t.total_amount for t in unpaid)
        }), 403
    
    # Create permit request
    permit = Permit(
        user_id=user_id,
        permit_type=data['permit_type'],
        property_id=data.get('property_id'),
        description=data.get('description'),
        status=PermitStatus.PENDING,
        submitted_date=datetime.utcnow(),
        taxes_paid=True,
        tax_payment_date=datetime.utcnow()
    )
    
    db.session.add(permit)
    db.session.commit()
    
    return jsonify({
        'message': 'Permit request submitted',
        'permit_id': permit.id,
        'permit_type': permit.permit_type.value,
        'status': permit.status.value,
        'submitted_date': permit.submitted_date.isoformat()
    }), 201

@blp.get('/my-requests')
@jwt_required()
@citizen_or_business_required
def get_my_permits():
    """Get user's permit requests"""
    user_id = get_current_user_id()
    
    permits = Permit.query.filter_by(user_id=user_id).all()
    
    return jsonify({
        'total': len(permits),
        'permits': [{
            'id': p.id,
            'permit_type': p.permit_type.value,
            'status': p.status.value,
            'submitted_date': p.submitted_date.isoformat() if p.submitted_date else None,
            'decision_date': p.decision_date.isoformat() if p.decision_date else None,
            'notes': p.notes
        } for p in permits]
    }), 200

@blp.get('/<int:permit_id>')
@jwt_required()
def get_permit(permit_id):
    """Get permit details with HATEOAS links"""
    from utils.hateoas import HATEOASBuilder
    
    user_id = get_current_user_id()
    user = User.query.get(user_id)
    
    permit = Permit.query.get(permit_id)
    
    if not permit:
        return jsonify({'error': ErrorMessages.NOT_FOUND}), 404
    
    # Check access
    if user.role not in [UserRole.MUNICIPAL_ADMIN, UserRole.URBANISM_OFFICER] and permit.user_id != user_id:
        return jsonify({'error': ErrorMessages.ACCESS_DENIED}), 403
    
    return jsonify({
        'id': permit.id,
        'user_id': permit.user_id,
        'permit_type': permit.permit_type.value,
        'status': permit.status.value,
        'property_id': permit.property_id,
        'description': permit.description,
        'taxes_paid': permit.taxes_paid,
        'submitted_date': permit.submitted_date.isoformat() if permit.submitted_date else None,
        'decision_date': permit.decision_date.isoformat() if permit.decision_date else None,
        'notes': permit.notes
    })
    
    response['_links'] = HATEOASBuilder.add_permit_links(permit)
    
    return jsonify(response), 200

@blp.get('/pending')
@jwt_required()
@urbanism_required
def get_pending_permits():
    """Get pending permit requests"""
    permits = Permit.query.filter_by(status=PermitStatus.PENDING).all()
    
    return jsonify({
        'total': len(permits),
        'permits': [{
            'id': p.id,
            'user_id': p.user_id,
            'permit_type': p.permit_type.value,
            'status': p.status.value,
            'submitted_date': p.submitted_date.isoformat() if p.submitted_date else None
        } for p in permits]
    }), 200

@blp.patch('/<int:permit_id>/decide')
@jwt_required()
@urbanism_required
def make_permit_decision(permit_id):
    """Make decision on permit request"""
    user_id = get_current_user_id()
    
    try:
        schema = PermitDecisionSchema()
        data = schema.load(request.get_json())
    except ValidationError as err:
        return jsonify({'errors': err.messages}), 400
    
    permit = Permit.query.get(permit_id)
    
    if not permit:
        return jsonify({'error': ErrorMessages.NOT_FOUND}), 404
    
    # Check if taxes are still paid (for approval)
    if data['status'] == 'approved':
        user = User.query.get(permit.user_id)
        taxes = Tax.query.filter(
            (Tax.property.has(owner_id=permit.user_id)) |
            (Tax.land.has(owner_id=permit.user_id))
        ).all()
        
        unpaid = [t for t in taxes if t.status != TaxStatus.PAID]
        
        if unpaid:
            return jsonify({
                'error': 'Taxes no longer paid - cannot approve',
                'message': ErrorMessages.UNPAID_TAXES
            }), 403
    
    permit.status = PermitStatus[data['status'].upper()]
    permit.decision_date = datetime.utcnow()
    permit.decision_by = user_id
    permit.notes = data.get('notes')
    
    db.session.commit()
    
    return jsonify({
        'message': 'Permit decision recorded',
        'permit_id': permit.id,
        'status': permit.status.value,
        'decision_date': permit.decision_date.isoformat()
    }), 200

@blp.get('/history')
@jwt_required()
@urbanism_required
def get_permit_history():
    """Get approved/rejected permit history for urbanism officers."""
    status_param = request.args.get('status')
    allowed_statuses = [PermitStatus.APPROVED, PermitStatus.REJECTED]
    
    if status_param:
        try:
            status_enum = PermitStatus[status_param.upper()]
        except KeyError:
            return jsonify({'error': 'Invalid status filter'}), 400
        allowed_statuses = [status_enum]
    
    permits = Permit.query.filter(Permit.status.in_(allowed_statuses))\
        .order_by(Permit.decision_date.desc(), Permit.submitted_date.desc())\
        .all()
    
    return jsonify({
        'total': len(permits),
        'permits': [{
            'id': p.id,
            'user_id': p.user_id,
            'permit_type': p.permit_type.value,
            'status': p.status.value,
            'submitted_date': p.submitted_date.isoformat() if p.submitted_date else None,
            'decision_date': p.decision_date.isoformat() if p.decision_date else None,
            'notes': p.notes
        } for p in permits]
    }), 200

@blp.get('/blocked')
@jwt_required()
@urbanism_required
def get_blocked_permits():
    """List permits automatically blocked by Article 13 (outstanding taxes)."""
    permits = Permit.query.filter_by(status=PermitStatus.PENDING).all()
    blocked = []

    for permit in permits:
        taxes = Tax.query.filter(
            (Tax.property.has(owner_id=permit.user_id)) |
            (Tax.land.has(owner_id=permit.user_id))
        ).all()

        # Refresh penalties
        any_updates = False
        for tax in taxes:
            if tax.status != TaxStatus.PAID:
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

        unpaid = [tax for tax in taxes if tax.status != TaxStatus.PAID]
        if not unpaid:
            continue

        outstanding = sum(tax.total_amount for tax in unpaid)
        blocked.append({
            'id': permit.id,
            'user_id': permit.user_id,
            'permit_type': permit.permit_type.value,
            'submitted_date': permit.submitted_date.isoformat() if permit.submitted_date else None,
            'outstanding_amount': round(outstanding, 2),
            'unpaid_taxes': len(unpaid)
        })

    return jsonify({
        'total': len(blocked),
        'blocked_permits': blocked
    }), 200
