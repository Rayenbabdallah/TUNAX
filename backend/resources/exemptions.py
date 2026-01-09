"""Tax Exemption Request routes"""
from flask import jsonify, request
from flask_smorest import Blueprint
from flask_jwt_extended import jwt_required
from utils.jwt_helpers import get_current_user_id
from extensions.db import db
from models.user import User, UserRole
from models.exemption import Exemption, ExemptionStatus, ExemptionType
from utils.role_required import citizen_or_business_required, admin_required
from utils.validators import ErrorMessages
from datetime import datetime
from marshmallow import Schema, fields

blp = Blueprint('exemptions', 'exemptions', url_prefix='/api/v1/exemptions')
exemptions_bp = blp


class ExemptionRequestSchema(Schema):
    """Schema for exemption requests"""
    exemption_type = fields.Str(required=True)
    reason = fields.Str(required=True)
    property_id = fields.Int(allow_none=True)
    land_id = fields.Int(allow_none=True)
    tax_id = fields.Int(allow_none=True)
    supporting_docs = fields.Str(allow_none=True)
    requested_amount = fields.Float(allow_none=True)


class ExemptionDecisionSchema(Schema):
    """Schema for exemption decisions"""
    decision = fields.Str(required=True)
    notes = fields.Str(allow_none=True)

@blp.post('/request')
@blp.arguments(ExemptionRequestSchema, location="json")
@blp.response(201)
@jwt_required()
@citizen_or_business_required
def request_exemption(data):
    """Request tax exemption"""
    user_id = get_current_user_id()
    
    if not data.get('exemption_type') or not data.get('reason'):
        return jsonify({'error': 'exemption_type and reason required'}), 400
    
    exemption = Exemption(
        user_id=user_id,
        exemption_type=data['exemption_type'],
        property_id=data.get('property_id'),
        land_id=data.get('land_id'),
        tax_id=data.get('tax_id'),
        reason=data['reason'],
        supporting_docs=data.get('supporting_docs'),
        requested_amount=data.get('requested_amount'),
        status=ExemptionStatus.PENDING,
        requested_date=datetime.utcnow()
    )
    
    db.session.add(exemption)
    db.session.commit()
    
    return jsonify({
        'message': 'Exemption request submitted',
        'exemption_id': exemption.id,
        'status': exemption.status.value
    }), 201

@blp.get('/my-exemptions')
@blp.response(200)
@jwt_required()
@citizen_or_business_required
def get_my_exemptions():
    """Get user's exemption requests"""
    user_id = get_current_user_id()
    
    exemptions = Exemption.query.filter_by(user_id=user_id).all()
    
    return jsonify({
        'total': len(exemptions),
        'exemptions': [{
            'id': e.id,
            'type': e.exemption_type,
            'reason': e.reason,
            'status': e.status.value,
            'requested_date': e.requested_date.isoformat() if e.requested_date else None,
            'decision_date': e.decision_date.isoformat() if e.decision_date else None
        } for e in exemptions]
    }), 200

@blp.get('/<int:exemption_id>')
@blp.response(200)
@jwt_required()
def get_exemption(exemption_id):
    """Get exemption details"""
    user_id = get_current_user_id()
    user = User.query.get(user_id)
    
    exemption = Exemption.query.get(exemption_id)
    
    if not exemption:
        return jsonify({'error': ErrorMessages.NOT_FOUND}), 404
    
    if user.role not in [UserRole.MUNICIPAL_ADMIN] and exemption.user_id != user_id:
        return jsonify({'error': ErrorMessages.ACCESS_DENIED}), 403
    
    return jsonify({
        'id': exemption.id,
        'user_id': exemption.user_id,
        'type': exemption.exemption_type,
        'reason': exemption.reason,
        'requested_amount': exemption.requested_amount,
        'status': exemption.status.value,
        'decision': exemption.decision,
        'admin_notes': exemption.admin_notes,
        'requested_date': exemption.requested_date.isoformat() if exemption.requested_date else None,
        'decision_date': exemption.decision_date.isoformat() if exemption.decision_date else None
    }), 200

@blp.patch('/<int:exemption_id>/decide')
@blp.arguments(ExemptionDecisionSchema, location="json")
@blp.response(200)
@jwt_required()
@admin_required
def decide_exemption(data, exemption_id):
    """Admin decides on exemption request"""
    user_id = get_current_user_id()
    
    if not data.get('decision') or data['decision'] not in ['approved', 'rejected', 'partial']:
        return jsonify({'error': 'decision must be approved, rejected, or partial'}), 400
    
    exemption = Exemption.query.get(exemption_id)
    
    if not exemption:
        return jsonify({'error': ErrorMessages.NOT_FOUND}), 404
    
    exemption.decision = data['decision']
    exemption.admin_notes = data.get('notes')
    exemption.decided_by = user_id
    exemption.decision_date = datetime.utcnow()
    exemption.status = ExemptionStatus.APPROVED if data['decision'] == 'approved' else ExemptionStatus.REJECTED
    
    db.session.commit()
    
    return jsonify({
        'message': 'Exemption decision recorded',
        'exemption_id': exemption_id,
        'decision': exemption.decision,
        'status': exemption.status.value
    }), 200
