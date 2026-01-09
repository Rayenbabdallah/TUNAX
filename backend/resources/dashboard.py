"""Dashboard and Analytics routes"""
from flask import jsonify, request
from flask_smorest import Blueprint
from flask_jwt_extended import jwt_required
from utils.jwt_helpers import get_current_user_id
from extensions.db import db
from models.user import User, UserRole
from models.property import Property
from models.land import Land
from models.tax import Tax, TaxType, TaxStatus
from models.payment import Payment
from models.permit import Permit, PermitStatus
from models.dispute import Dispute, DisputeStatus
from models.inspection import Inspection, InspectionStatus
from utils.role_required import admin_required, inspector_required, citizen_or_business_required
from utils.calculator import TaxCalculator
from marshmallow import Schema

blp = Blueprint('dashboard', 'dashboard', url_prefix='/api/v1/dashboard')
dashboard_bp = blp


@blp.get('/citizen-summary')
@blp.response(200)
@jwt_required()
@citizen_or_business_required
def citizen_summary():
    """Get citizen dashboard summary"""
    user_id = get_current_user_id()
    
    # Get properties and lands
    properties = Property.query.filter_by(owner_id=user_id).count()
    lands = Land.query.filter_by(owner_id=user_id).count()
    
    # Get tax summary
    taxes = Tax.query.filter(
        (Tax.property.has(owner_id=user_id)) | 
        (Tax.land.has(owner_id=user_id))
    ).all()
    
    # Compute dynamic penalties and totals
    total_tax = 0.0
    paid_taxes = 0.0
    unpaid_taxes = 0.0
    any_updates = False
    
    for tax in taxes:
        if tax.status != TaxStatus.PAID:
            # Recompute penalty dynamically based on current date
            section = 'TIB' if tax.tax_type == TaxType.TIB else 'TTNB'
            new_penalty = TaxCalculator.compute_late_payment_penalty_for_year(
                tax_amount=tax.tax_amount,
                tax_year=tax.tax_year,
                section=section
            )
            if (tax.penalty_amount or 0.0) != new_penalty or (tax.total_amount or 0.0) != (tax.tax_amount + new_penalty):
                tax.penalty_amount = new_penalty
                tax.total_amount = tax.tax_amount + new_penalty
                any_updates = True
        
        # Use total_amount (tax + penalty) in dashboard calculations
        total_with_penalty = tax.total_amount if tax.total_amount else tax.tax_amount
        total_tax += total_with_penalty
        
        if tax.status == TaxStatus.PAID:
            paid_taxes += total_with_penalty
        else:
            unpaid_taxes += total_with_penalty
    
    if any_updates:
        db.session.commit()
    
    # Get permits
    pending_permits = Permit.query.filter_by(user_id=user_id, status=PermitStatus.PENDING).count()
    approved_permits = Permit.query.filter_by(user_id=user_id, status=PermitStatus.APPROVED).count()
    
    # Get disputes
    active_disputes = Dispute.query.filter_by(claimant_id=user_id).filter(
        Dispute.status != DisputeStatus.RESOLVED
    ).count()
    
    return jsonify({
        'properties': properties,
        'lands': lands,
        'taxes': {
            'total': round(total_tax, 2),
            'paid': round(paid_taxes, 2),
            'unpaid': round(unpaid_taxes, 2),
            'count': len(taxes)
        },
        'permits': {
            'pending': pending_permits,
            'approved': approved_permits
        },
        'active_disputes': active_disputes
    }), 200

@blp.get('/admin-overview')
@blp.response(200)
@jwt_required()
@admin_required
def admin_overview():
    """Get admin dashboard overview"""
    total_users = User.query.count()
    total_properties = Property.query.count()
    total_lands = Land.query.count()
    
    total_taxes = Tax.query.count()
    paid_taxes = Tax.query.filter_by(status=TaxStatus.PAID).count()
    pending_taxes = Tax.query.filter(Tax.status != TaxStatus.PAID).count()
    
    total_revenue = db.session.query(db.func.sum(Payment.amount)).scalar() or 0
    total_payments = Payment.query.count()
    
    pending_permits = Permit.query.filter_by(status=PermitStatus.PENDING).count()
    pending_disputes = Dispute.query.filter(Dispute.status != DisputeStatus.RESOLVED).count()
    
    return jsonify({
        'users': total_users,
        'properties': total_properties,
        'lands': total_lands,
        'taxes': {
            'total': total_taxes,
            'paid': paid_taxes,
            'pending': pending_taxes
        },
        'revenue': {
            'total_collected': round(float(total_revenue), 2),
            'payment_count': total_payments
        },
        'permits': {
            'pending': pending_permits
        },
        'disputes': {
            'pending': pending_disputes
        }
    }), 200

@blp.get('/inspector-workload')
@blp.response(200)
@jwt_required()
@inspector_required
def inspector_workload():
    """Get inspector workload summary (municipality-specific)"""
    user_id = get_current_user_id()
    user = User.query.get(user_id)
    
    # Get properties/lands awaiting inspection IN INSPECTOR'S MUNICIPALITY
    properties_to_inspect = Property.query.filter_by(
        satellite_verified=False,
        commune_id=user.commune_id
    ).count()
    lands_to_inspect = Land.query.filter_by(
        satellite_verified=False,
        commune_id=user.commune_id
    ).count()
    
    # Get inspections completed by this inspector
    completed_inspections = Inspection.query.filter_by(
        inspector_id=user_id,
        status=InspectionStatus.COMPLETED
    ).count()
    
    # Get pending inspections
    pending_inspections = Inspection.query.filter(
        Inspection.inspector_id == user_id,
        Inspection.status != InspectionStatus.COMPLETED
    ).count()
    
    return jsonify({
        'pending_work': {
            'properties': properties_to_inspect,
            'lands': lands_to_inspect
        },
        'completed': completed_inspections,
        'in_progress': pending_inspections
    }), 200
