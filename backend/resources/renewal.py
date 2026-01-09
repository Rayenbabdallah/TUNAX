"""Tax Renewal routes"""
from flask import jsonify
from flask_smorest import Blueprint
from flask_jwt_extended import jwt_required
from utils.jwt_helpers import get_current_user_id
from extensions.db import db
from models.property import Property
from models.land import Land
from models.tax import Tax, TaxType, TaxStatus
from utils.calculator import TaxCalculator
from utils.role_required import citizen_or_business_required
from utils.validators import ErrorMessages
from datetime import datetime
from marshmallow import Schema

blp = Blueprint('renewal', 'renewal', url_prefix='/api/v1/renewal')


class RenewalSchema(Schema):
    """Schema for tax renewal"""
    pass  # No required fields for renewal


@blp.post('/properties/<int:property_id>/renew')
@blp.arguments(RenewalSchema, location="json", required=False)
@blp.response(200)
@jwt_required()
@citizen_or_business_required
def renew_property_tax(property_id, args):
    """Renew annual property tax declaration"""
    user_id = get_current_user_id()
    prop = Property.query.get(property_id)
    
    if not prop:
        return jsonify({'error': ErrorMessages.NOT_FOUND}), 404
    
    if prop.owner_id != user_id:
        return jsonify({'error': ErrorMessages.ACCESS_DENIED}), 403
    
    current_year = datetime.now().year
    new_year = current_year + 1
    
    # Check if already renewed for next year
    existing = Tax.query.filter_by(
        property_id=property_id,
        tax_type=TaxType.TIB,
        tax_year=new_year
    ).first()
    
    if existing:
        return jsonify({'error': 'Property tax already renewed for next year'}), 400
    
    # Recalculate for new year
    calc_result = TaxCalculator.calculate_tib(prop)
    
    new_tax = Tax(
        property_id=property_id,
        tax_type=TaxType.TIB,
        tax_year=new_year,
        base_amount=calc_result['base_amount'],
        rate_percent=calc_result['rate_percent'],
        tax_amount=calc_result['tax_amount'],
        total_amount=calc_result['total_amount'],
        status=TaxStatus.CALCULATED
    )
    
    db.session.add(new_tax)
    db.session.commit()
    
    return jsonify({
        'message': 'Property tax renewed for next year',
        'property_id': property_id,
        'new_tax_year': new_year,
        'tax_id': new_tax.id,
        'tax_amount': new_tax.tax_amount,
        'total_amount': new_tax.total_amount
    }), 201

@blp.post('/lands/<int:land_id>/renew')
@blp.arguments(RenewalSchema, location="json", required=False)
@blp.response(200)
@jwt_required()
@citizen_or_business_required
def renew_land_tax(land_id, args):
    """Renew annual land tax declaration"""
    user_id = get_current_user_id()
    land = Land.query.get(land_id)
    
    if not land:
        return jsonify({'error': ErrorMessages.NOT_FOUND}), 404
    
    if land.owner_id != user_id:
        return jsonify({'error': ErrorMessages.ACCESS_DENIED}), 403
    
    current_year = datetime.now().year
    new_year = current_year + 1
    
    # Check if already renewed for next year
    existing = Tax.query.filter_by(
        land_id=land_id,
        tax_type=TaxType.TTNB,
        tax_year=new_year
    ).first()
    
    if existing:
        return jsonify({'error': 'Land tax already renewed for next year'}), 400
    
    # Recalculate for new year
    calc_result = TaxCalculator.calculate_ttnb(land)
    
    if 'error' in calc_result:
        return jsonify({'error': calc_result['error']}), 400
    
    new_tax = Tax(
        land_id=land_id,
        tax_type=TaxType.TTNB,
        tax_year=new_year,
        base_amount=calc_result['base_amount'],
        rate_percent=calc_result['rate_percent'],
        tax_amount=calc_result['tax_amount'],
        total_amount=calc_result['total_amount'],
        status=TaxStatus.CALCULATED
    )
    
    db.session.add(new_tax)
    db.session.commit()
    
    return jsonify({
        'message': 'Land tax renewed for next year',
        'land_id': land_id,
        'new_tax_year': new_year,
        'tax_id': new_tax.id,
        'tax_amount': new_tax.tax_amount,
        'total_amount': new_tax.total_amount
    }), 201

# Route aliases for test compatibility
@blp.post('/property/<int:property_id>')
@blp.response(201)
@jwt_required()
@citizen_or_business_required
def renew_property_alias(property_id):
    """Alias: renew property tax"""
    user_id = get_current_user_id()
    prop = Property.query.get(property_id)
    
    if not prop:
        return jsonify({'error': ErrorMessages.NOT_FOUND}), 404
    
    if prop.owner_id != user_id:
        return jsonify({'error': ErrorMessages.ACCESS_DENIED}), 403
    
    current_year = datetime.now().year
    new_year = current_year + 1
    
    existing = Tax.query.filter_by(
        property_id=property_id,
        tax_type=TaxType.TIB,
        tax_year=new_year
    ).first()
    
    if existing:
        return jsonify({'error': 'Property tax already renewed for next year'}), 400
    
    calc_result = TaxCalculator.calculate_tib(prop)
    
    new_tax = Tax(
        property_id=property_id,
        tax_type=TaxType.TIB,
        tax_year=new_year,
        base_amount=calc_result['base_amount'],
        rate_percent=calc_result['rate_percent'],
        tax_amount=calc_result['tax_amount'],
        total_amount=calc_result['total_amount'],
        status=TaxStatus.CALCULATED
    )
    
    db.session.add(new_tax)
    db.session.commit()
    
    return jsonify({
        'message': 'Property tax renewed for next year',
        'property_id': property_id,
        'new_tax_year': new_year,
        'tax_id': new_tax.id,
        'tax_amount': new_tax.tax_amount,
        'total_amount': new_tax.total_amount
    }), 201

@blp.post('/land/<int:land_id>')
@blp.response(201)
@jwt_required()
@citizen_or_business_required
def renew_land_alias(land_id):
    """Alias: renew land tax"""
    user_id = get_current_user_id()
    land = Land.query.get(land_id)
    
    if not land:
        return jsonify({'error': ErrorMessages.NOT_FOUND}), 404
    
    if land.owner_id != user_id:
        return jsonify({'error': ErrorMessages.ACCESS_DENIED}), 403
    
    current_year = datetime.now().year
    new_year = current_year + 1
    
    existing = Tax.query.filter_by(
        land_id=land_id,
        tax_type=TaxType.TTNB,
        tax_year=new_year
    ).first()
    
    if existing:
        return jsonify({'error': 'Land tax already renewed for next year'}), 400
    
    calc_result = TaxCalculator.calculate_ttnb(land)
    
    if 'error' in calc_result:
        return jsonify({'error': calc_result['error']}), 400
    
    new_tax = Tax(
        land_id=land_id,
        tax_type=TaxType.TTNB,
        tax_year=new_year,
        base_amount=calc_result['base_amount'],
        rate_percent=calc_result['rate_percent'],
        tax_amount=calc_result['tax_amount'],
        total_amount=calc_result['total_amount'],
        status=TaxStatus.CALCULATED
    )
    
    db.session.add(new_tax)
    db.session.commit()
    
    return jsonify({
        'message': 'Land tax renewed for next year',
        'land_id': land_id,
        'new_tax_year': new_year,
        'tax_id': new_tax.id,
        'tax_amount': new_tax.tax_amount,
        'total_amount': new_tax.total_amount
    }), 201

# Amendments Blueprint - declarations can be amended before finalization
amendments_bp = Blueprint('amendments', __name__, url_prefix='/api/v1/amendments')

@amendments_bp.post('/property/<int:property_id>')
@jwt_required()
@citizen_or_business_required
def amend_property(property_id):
    """Amend property declaration"""
    return jsonify({
        'message': 'Property amendment feature coming soon',
        'property_id': property_id,
        'status': 'not_implemented'
    }), 200

@amendments_bp.post('/land/<int:land_id>')
@jwt_required()
@citizen_or_business_required
def amend_land(land_id):
    """Amend land declaration"""
    return jsonify({
        'message': 'Land amendment feature coming soon',
        'land_id': land_id,
        'status': 'not_implemented'
    }), 200
