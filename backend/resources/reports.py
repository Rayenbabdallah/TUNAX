"""Reporting and Bulk Operations routes"""
from flask import jsonify, request, send_file
from flask_smorest import Blueprint
from flask_jwt_extended import jwt_required
from utils.jwt_helpers import get_current_user_id
from extensions.db import db
from models.user import User, UserRole
from models.property import Property
from models.land import Land
from models.tax import Tax, TaxStatus, TaxType
from models.payment import Payment
from utils.role_required import admin_required, finance_required, citizen_or_business_required
from utils.calculator import TaxCalculator
from datetime import datetime
from marshmallow import Schema, fields
import csv
import io

blp = Blueprint('reports', 'reports', url_prefix='/api/v1/reports')
admin_bulk_bp = Blueprint('admin_bulk', 'admin_bulk', url_prefix='/api/v1/admin')


class ExportFiltersSchema(Schema):
    """Schema for export filters"""
    city = fields.Str(allow_none=True)
    property_type = fields.Str(allow_none=True)
    min_surface = fields.Float(allow_none=True)
    max_surface = fields.Float(allow_none=True)


class BulkPropertiesSchema(Schema):
    """Schema for bulk properties operation"""
    property_ids = fields.List(fields.Int(), required=True)


@blp.get('/export/properties')
@blp.arguments(ExportFiltersSchema, location="query", required=False)
@blp.response(200)
@jwt_required()
@admin_required
def export_properties_report(filters=None):
    
    filters = filters or {}
    query = Property.query
    
    if filters.get('city'):
        query = query.filter(Property.city.ilike(f"%{filters['city']}%"))
    if filters.get('affectation'):
        query = query.filter_by(affectation=filters['affectation'])
    
    properties = query.all()
    
    # Create CSV in memory
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['ID', 'Owner', 'Street', 'City', 'Surface', 'Affectation', 'Price', 'Tax Status'])
    
    for prop in properties:
        tax = Tax.query.filter_by(property_id=prop.id).first()
        owner = User.query.get(prop.owner_id)
        owner_username = owner.username if owner else 'Unknown'
        writer.writerow([
            prop.id,
            owner_username,
            prop.street_address,
            prop.city,
            prop.surface_couverte,
            prop.affectation.value if hasattr(prop.affectation, 'value') else prop.affectation,
            prop.reference_price_per_m2,
            tax.status.value if tax else 'N/A'
        ])
    
    return jsonify({
        'message': 'Export ready',
        'count': len(properties),
        'csv': output.getvalue()
    }), 200

@blp.get('/delinquency')
@blp.response(200)
@jwt_required()
@finance_required
def delinquency_report():
    """Get overdue taxes report"""
    days_overdue = request.args.get('days', 30, type=int)
    
    # Get unpaid taxes
    unpaid = Tax.query.filter(
        Tax.status != TaxStatus.PAID
    ).all()
    # Refresh penalties for unpaid taxes
    any_updates = False
    for t in unpaid:
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

    debtors = {}
    for tax in unpaid:
        if tax.property:
            user_id = tax.property.owner_id
        elif tax.land:
            user_id = tax.land.owner_id
        else:
            continue
        
        if user_id not in debtors:
            user = User.query.get(user_id)
            debtors[user_id] = {
                'username': user.username,
                'email': user.email,
                'total_overdue': 0,
                'tax_count': 0
            }
        
        debtors[user_id]['total_overdue'] += tax.total_amount
        debtors[user_id]['tax_count'] += 1
    
    return jsonify({
        'total_debtors': len(debtors),
        'total_overdue_amount': sum(d['total_overdue'] for d in debtors.values()),
        'debtors': list(debtors.values())
    }), 200

@blp.post('/bulk/properties')
@blp.arguments(BulkPropertiesSchema, location="json")
@blp.response(200)
@jwt_required()
@admin_required
def bulk_declare_properties(data):
    """Bulk import properties"""
    
    if not isinstance(data.get('properties'), list):
        return jsonify({'error': 'properties array required'}), 400
    
    from utils.calculator import TaxCalculator
    
    created = 0
    errors = []
    
    for idx, prop_data in enumerate(data['properties']):
        try:
            user = User.query.filter_by(username=prop_data['owner_username']).first()
            if not user:
                errors.append(f"Row {idx+1}: User {prop_data['owner_username']} not found")
                continue
            
            prop = Property(
                owner_id=user.id,
                street_address=prop_data['street_address'],
                city=prop_data['city'],
                surface_couverte=prop_data['surface_couverte'],
                reference_price=prop_data['reference_price'],
                affectation=prop_data.get('affectation', 'residential')
            )
            
            db.session.add(prop)
            db.session.flush()
            
            # Calculate tax
            calc_result = TaxCalculator.calculate_tib(prop)
            tax = Tax(
                property_id=prop.id,
                tax_type=TaxType.TIB,
                tax_year=datetime.now().year,
                base_amount=calc_result['base_amount'],
                rate_percent=calc_result['rate_percent'],
                tax_amount=calc_result['tax_amount'],
                total_amount=calc_result['total_amount'],
                status=TaxStatus.CALCULATED
            )
            
            db.session.add(tax)
            created += 1
        except Exception as e:
            errors.append(f"Row {idx+1}: {str(e)}")
    
    db.session.commit()
    
    return jsonify({
        'message': 'Bulk import completed',
        'created': created,
        'errors': errors
    }), 201

@blp.post('/bulk/payment')
@blp.arguments(BulkPropertiesSchema, location="json")
@blp.response(201)
@jwt_required()
@finance_required
def bulk_payment(data):
    """Process bulk payments"""
    
    if not isinstance(data.get('payments'), list):
        return jsonify({'error': 'payments array required'}), 400
    
    processed = 0
    errors = []
    
    for idx, payment_data in enumerate(data['payments']):
        try:
            tax = Tax.query.get(payment_data['tax_id'])
            if not tax:
                errors.append(f"Row {idx+1}: Tax {payment_data['tax_id']} not found")
                continue
            
            payment = Payment(
                user_id=tax.property.owner_id if tax.property else tax.land.owner_id,
                tax_id=tax.id,
                amount=payment_data['amount'],
                method=payment_data.get('method', 'bank_transfer'),
                status=PaymentStatus.COMPLETED,
                reference_number=f"BULK-{secrets.token_hex(8).upper()}"
            )
            
            tax.status = TaxStatus.PAID
            db.session.add(payment)
            processed += 1
        except Exception as e:
            errors.append(f"Row {idx+1}: {str(e)}")
    
    db.session.commit()
    
    return jsonify({
        'message': 'Bulk payments processed',
        'processed': processed,
        'errors': errors
    }), 201
