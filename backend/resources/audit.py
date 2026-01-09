"""Audit trail and history routes"""
from flask import jsonify, request
from flask_smorest import Blueprint
from flask_jwt_extended import jwt_required
from utils.jwt_helpers import get_current_user_id
from models.audit_log import AuditLog
from models.tax import Tax
from utils.role_required import admin_required
from utils.validators import ErrorMessages
from datetime import datetime, timedelta
from marshmallow import Schema

blp = Blueprint('audit', 'audit', url_prefix='/api/v1/audit')
audit_bp = blp


class AuditQuerySchema(Schema):
    """Schema for audit log queries"""
    pass


@blp.get('/logs')
@blp.response(200)
@jwt_required()
@admin_required
def get_audit_logs():
    """Get audit logs"""
    entity_type = request.args.get('entity_type')
    entity_id = request.args.get('entity_id', type=int)
    action = request.args.get('action')
    user_id = request.args.get('user_id', type=int)
    days = request.args.get('days', 30, type=int)
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    
    since = datetime.utcnow() - timedelta(days=days)
    query = AuditLog.query.filter(AuditLog.timestamp >= since)
    
    if entity_type:
        query = query.filter_by(entity_type=entity_type)
    if entity_id:
        query = query.filter_by(entity_id=entity_id)
    if action:
        query = query.filter_by(action=action)
    if user_id:
        query = query.filter_by(user_id=user_id)
    
    results = query.order_by(AuditLog.timestamp.desc()).paginate(page=page, per_page=per_page)
    
    return jsonify({
        'total': results.total,
        'page': page,
        'per_page': per_page,
        'logs': [{
            'id': log.id,
            'entity_type': log.entity_type,
            'entity_id': log.entity_id,
            'action': log.action,
            'user_id': log.user_id,
            'changes': log.changes,
            'timestamp': log.timestamp.isoformat() if log.timestamp else None
        } for log in results.items]
    }), 200

@blp.get('/tax/<int:tax_id>')
@blp.response(200)
@jwt_required()
@admin_required
def get_tax_history(tax_id):
    """Get tax calculation and payment history"""
    tax = Tax.query.get(tax_id)
    
    if not tax:
        return jsonify({'error': ErrorMessages.NOT_FOUND}), 404
    
    # Get audit logs for this tax
    logs = AuditLog.query.filter_by(
        entity_type='tax',
        entity_id=tax_id
    ).order_by(AuditLog.timestamp.asc()).all()
    
    # Get related payments
    from models.payment import Payment
    payments = Payment.query.filter_by(tax_id=tax_id).all()
    
    return jsonify({
        'tax_id': tax_id,
        'history': [{
            'action': log.action,
            'changes': log.changes,
            'timestamp': log.timestamp.isoformat() if log.timestamp else None
        } for log in logs],
        'payments': [{
            'id': p.id,
            'amount': p.amount,
            'method': p.method.value,
            'reference': p.reference_number,
            'date': p.payment_date.isoformat() if p.payment_date else None
        } for p in payments]
    }), 200
