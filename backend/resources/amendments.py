"""Property and Land Amendment routes"""
from flask import jsonify, request
from flask_smorest import Blueprint
from flask_jwt_extended import jwt_required
from utils.jwt_helpers import get_current_user_id
from extensions.db import db
from models.user import User, UserRole
from models.property import Property, PropertyStatus
from models.land import Land, LandStatus
from models.tax import Tax, TaxType
from utils.calculator import TaxCalculator
from utils.role_required import citizen_or_business_required
from utils.validators import ErrorMessages, Validators
from datetime import datetime
from marshmallow import Schema, fields

blp = Blueprint('amendments', 'amendments', url_prefix='/api/v1/amendments')


class PropertyAmendmentSchema(Schema):
    """Schema for property amendments"""
    property_type = fields.Str(allow_none=True)
    surface_area = fields.Float(allow_none=True)
    street_address = fields.Str(allow_none=True)
    city = fields.Str(allow_none=True)
    postal_code = fields.Str(allow_none=True)


class LandAmendmentSchema(Schema):
    """Schema for land amendments"""
    land_type = fields.Str(allow_none=True)
    surface = fields.Float(allow_none=True)
    street_address = fields.Str(allow_none=True)
    city = fields.Str(allow_none=True)
    postal_code = fields.Str(allow_none=True)


@blp.patch('/properties/<int:property_id>')
@blp.arguments(PropertyAmendmentSchema, location="json")
@blp.response(200)
@jwt_required()
@citizen_or_business_required
def update_property(data, property_id):
    """Update property details"""
    user_id = get_current_user_id()
    prop = Property.query.get(property_id)
    
    if not prop:
        return jsonify({'error': ErrorMessages.NOT_FOUND}), 404
    if prop.owner_id != user_id:
        return jsonify({'error': ErrorMessages.ACCESS_DENIED}), 403
    
    data = request.get_json()
    
    # Allow updates only for specific fields
    if 'surface_couverte' in data:
        prop.surface_couverte = data['surface_couverte']
    if 'surface_totale' in data:
        prop.surface_totale = data['surface_totale']
    if 'nb_floors' in data:
        prop.nb_floors = data['nb_floors']
    if 'nb_rooms' in data:
        prop.nb_rooms = data['nb_rooms']
    if 'reference_price' in data:
        prop.reference_price = data['reference_price']
    if 'service_rate' in data:
        prop.service_rate = data['service_rate']
    if 'affectation' in data:
        prop.affectation = data['affectation']
    
    prop.updated_at = datetime.utcnow()
    
    # Recalculate taxes if price/surface changed
    if 'reference_price' in data or 'surface_couverte' in data:
        tax = Tax.query.filter_by(property_id=property_id, tax_type=TaxType.TIB).first()
        if tax:
            calc_result = TaxCalculator.calculate_tib(prop)
            tax.base_amount = calc_result['base_amount']
            tax.rate_percent = calc_result['rate_percent']
            tax.tax_amount = calc_result['tax_amount']
            tax.total_amount = calc_result['total_amount']
    
    db.session.commit()
    
    return jsonify({
        'message': 'Property updated successfully',
        'property_id': property_id,
        'updated_at': prop.updated_at.isoformat()
    }), 200

@blp.patch('/lands/<int:land_id>')
@blp.arguments(LandAmendmentSchema, location="json")
@blp.response(200)
@jwt_required()
@citizen_or_business_required
def update_land(data, land_id):
    """Update land details"""
    user_id = get_current_user_id()
    land = Land.query.get(land_id)
    if not land:
        return jsonify({'error': ErrorMessages.NOT_FOUND}), 404
    
    if land.owner_id != user_id:
        return jsonify({'error': ErrorMessages.ACCESS_DENIED}), 403
    
    data = request.get_json()
    
    # Allow updates only for specific fields
    if 'surface' in data:
        land.surface = data['surface']
    if 'vénale_value' in data:
        land.vénale_value = data['vénale_value']
    if 'tariff_value' in data:
        land.tariff_value = data['tariff_value']
    if 'land_type' in data:
        land.land_type = data['land_type']
    
    land.updated_at = datetime.utcnow()
    
    # Recalculate taxes if value/surface changed
    if 'vénale_value' in data or 'surface' in data:
        tax = Tax.query.filter_by(land_id=land_id, tax_type=TaxType.TTNB).first()
        if tax:
            calc_result = TaxCalculator.calculate_ttnb(land)
            tax.base_amount = calc_result['base_amount']
            tax.rate_percent = calc_result['rate_percent']
            tax.tax_amount = calc_result['tax_amount']
            tax.total_amount = calc_result['total_amount']
    
    db.session.commit()
    
    return jsonify({
        'message': 'Land updated successfully',
        'land_id': land_id,
        'updated_at': land.updated_at.isoformat()
    }), 200
