"""TTNB (Taxe sur les Terrains Non Bâtis) management routes (flask-smorest)"""
from flask import jsonify, request
from flask_smorest import Blueprint
from flask_jwt_extended import jwt_required
from utils.jwt_helpers import get_current_user_id
from extensions.db import db
from models.user import User, UserRole
from models.land import Land, LandStatus
from models.tax import Tax, TaxType, TaxStatus
from models import Commune
from models import Declaration, DeclarationType


from schemas.tax_permit import LandCreateSchema, LandSchema, TaxResultSchema
from utils.calculator import TaxCalculator
from utils.geo import GeoLocator
from utils.email_notifier import send_tax_declaration_confirmation
from utils.role_required import citizen_or_business_required, municipality_required
from utils.validators import Validators, ErrorMessages
from datetime import datetime

blp = Blueprint('ttnb', 'ttnb', url_prefix='/api/v1/ttnb')

# Valid urban zones per Décret 2017-396
VALID_URBAN_ZONES = {
    'haute_densite': 'Haute densité (1.200 TND/m²)',
    'densite_moyenne': 'Densité moyenne (0.800 TND/m²)',
    'faible_densite': 'Faible densité (0.400 TND/m²)',
    'peripherique': 'Périphérique (0.200 TND/m²)'
}

@blp.post('/lands')
@jwt_required()
@citizen_or_business_required
@blp.arguments(LandCreateSchema)
@blp.response(201, LandSchema)
def declare_land(data):
    """Declare a new land (TTNB) with urban zone (per Décret 2017-396)"""
    user_id = get_current_user_id()
    user = User.query.get(user_id)
    
    # REQUIRED: urban_zone must be specified for TTNB calculation
    urban_zone = data.get('urban_zone')
    if not urban_zone:
        return jsonify({
            'error': 'Urban zone required',
            'message': 'Land must be classified with an urban zone for TTNB calculation per Décret 2017-396.',
            'valid_zones': VALID_URBAN_ZONES
        }), 400
    
    if urban_zone not in VALID_URBAN_ZONES:
        return jsonify({
            'error': 'Invalid urban zone',
            'message': f'Urban zone must be one of: {list(VALID_URBAN_ZONES.keys())}',
            'valid_zones': VALID_URBAN_ZONES
        }), 400
    
    # REQUIRED: Citizens/businesses MUST specify commune_id for each land declaration
    # (They are not bound to a single commune - can have lands in multiple municipalities)
    commune_id = data.get('commune_id')
    if not commune_id:
        return jsonify({
            'error': 'Commune required',
            'message': 'Land must be declared for a specific commune. Provide commune_id in the request body.'
        }), 400
    
    # Verify commune exists
    commune = Commune.query.get(commune_id)
    if not commune:
        return jsonify({'error': f'Commune with ID {commune_id} not found'}), 404
    
    # If structured address provided, compose the canonical address fields
    if data.get('address_mode') in ['villa', 'residence']:
        street = (data.get('street_name') or '').strip()
        locality = (data.get('locality') or '').strip()
        if data['address_mode'] == 'villa':
            villa_no = (data.get('villa_number') or '').strip()
            composed = f"Villa {villa_no}, {street}"
        else:
            res_name = (data.get('residence_name') or '').strip()
            apt_no = (data.get('apartment_number') or '').strip()
            composed = f"Résidence {res_name}, Apt {apt_no}, {street}"
        if locality:
            composed = f"{composed}, {locality}"
        data['street_address'] = composed
        data['city'] = commune.nom_municipalite_fr
        if locality:
            data['delegation'] = locality

    # Determine coordinates: prefer provided when available
    latitude = data.get('latitude')
    longitude = data.get('longitude')
    if latitude is None or longitude is None:
        # Try to geocode address using Nominatim
        latitude, longitude = GeoLocator.geocode_address(
            data['street_address'],
            data['city']
        )
    
    # If Nominatim fails, require explicit GPS coordinates
    if latitude is None or longitude is None:
        # Check if user provided fallback coordinates
        if not data.get('latitude') or not data.get('longitude'):
            nearby = GeoLocator.get_nearby_streets(data['city'], data['street_address'])
            return jsonify({
                'error': 'Address not found via Nominatim. Please provide GPS coordinates.',
                'message': f"Could not geocode '{data['street_address']}, {data['city']}'. Nearby streets: {nearby[:3]}",
                'suggestions': nearby[:5],
                'required_fields': ['latitude', 'longitude']
            }), 400
        # Use provided coordinates
        latitude = float(data['latitude'])
        longitude = float(data['longitude'])
    
    # Validate coordinates are within Tunisia bounds (rough check)
    if not (32.0 <= latitude <= 37.5 and 7.0 <= longitude <= 12.0):
        return jsonify({
            'error': 'Coordinates outside Tunisia bounds',
            'message': 'Land coordinates must be within Tunisia (lat: 32-37.5, lon: 7-12)'
        }), 400
    
    # Create land with urban_zone and commune_id
    land_obj = Land(
        owner_id=user_id,
        commune_id=commune_id,
        street_address=data['street_address'],
        city=data['city'],
        delegation=data.get('delegation'),
        post_code=data.get('post_code'),
        latitude=latitude,
        longitude=longitude,
        surface=data['surface'],
        land_type=data['land_type'],
        urban_zone=urban_zone,  # REQUIRED for TTNB (Décret 2017-396)
        is_exempt=data.get('is_exempt', False),
        exemption_reason=data.get('exemption_reason'),
        status=LandStatus.DECLARED
    )
    
    db.session.add(land_obj)
    try:
        db.session.flush()
    except Exception as e:
        db.session.rollback()
        if 'unique_land_per_owner_commune' in str(e):
            return jsonify({'error': 'Land already exists', 'message': 'You have already declared a land with this address in this commune'}), 409
        return jsonify({'error': 'Database error', 'message': str(e)}), 500

    # Create declaration record to enable document attachments and reviews
    declaration = Declaration(
        owner_id=user_id,
        commune_id=commune_id,
        declaration_type=DeclarationType.LAND.value,
        reference_id=land_obj.id,
        status="submitted",
    )
    db.session.add(declaration)
    db.session.flush()
    
    # Calculate TTNB using new legally-correct formula (surface × zone_tariff)
    calc_result = TaxCalculator.calculate_ttnb(land_obj)
    
    if 'error' in calc_result:
        db.session.rollback()
        return jsonify({'error': calc_result['error'], 'message': calc_result.get('message')}), 400
    
    tax = Tax(
        land_id=land_obj.id,
        tax_type=TaxType.TTNB,
        tax_year=datetime.now().year,
        base_amount=land_obj.surface,  # Base is the surface
        rate_percent=calc_result.get('tariff_per_m2'),  # Store the tariff as rate
        tax_amount=calc_result['tax_amount'],
        total_amount=calc_result['total_amount'],
        status=TaxStatus.CALCULATED
    )
    
    db.session.add(tax)
    db.session.commit()
    
    # Send tax declaration confirmation email
    if user and user.email:
        send_tax_declaration_confirmation(
            user_email=user.email,
            user_name=user.first_name or user.username,
            tax_id=str(tax.id),
            property_address=f"{data['street_address']}, {data['city']}",
            tax_amount=calc_result['tax_amount']
        )
    
    return jsonify({
        'message': 'Land declared successfully with legally-correct TTNB calculation (Décret 2017-396)',
        'land_id': land_obj.id,
        'commune_id': commune_id,
        'declaration_id': declaration.id,
        'urban_zone': urban_zone,
        'tax_id': tax.id,
        'tax_calculation': {
            'surface_m2': land_obj.surface,
            'tariff_per_m2': calc_result.get('tariff_per_m2'),
            'ttnb_amount': calc_result['tax_amount'],
        }
    }), 201

@blp.get('/lands')
@jwt_required()
@municipality_required
def get_lands():
    """Get lands (filtered by user's commune for municipal staff)"""
    user_id = get_current_user_id()
    user = User.query.get(user_id)
    
    # Citizens/businesses see only their own lands
    if user.role in [UserRole.CITIZEN, UserRole.BUSINESS]:
        lands = Land.query.filter_by(owner_id=user_id).all()
    # Municipal staff see all lands in their commune
    elif user.role in [UserRole.MUNICIPAL_AGENT, UserRole.INSPECTOR, UserRole.MUNICIPAL_ADMIN]:
        lands = Land.query.filter_by(commune_id=user.commune_id).all()
    # Ministry admin sees all lands
    else:
        lands = Land.query.all()
    
    result = []
    any_updates = False
    for land in lands:
        tax = Tax.query.filter_by(land_id=land.id, tax_type=TaxType.TTNB).first()
        if tax and tax.status != TaxStatus.PAID:
            new_penalty = TaxCalculator.compute_late_payment_penalty_for_year(
                tax_amount=tax.tax_amount,
                tax_year=tax.tax_year,
                section='TTNB'
            )
            if (tax.penalty_amount or 0.0) != new_penalty or (tax.total_amount or 0.0) != (tax.tax_amount + new_penalty):
                tax.penalty_amount = new_penalty
                tax.total_amount = tax.tax_amount + new_penalty
                any_updates = True
        from datetime import date as _date
        _start = _date(int(tax.tax_year) + 1, 1, 1) if tax else None
        _is_payable = (_date.today() >= _start) if _start else False
        _payable_from = _start.isoformat() if _start else None
        result.append({
            'id': land.id,
            'owner_id': land.owner_id,
            'commune_id': land.commune_id,
            'street_address': land.street_address,
            'city': land.city,
            'surface': land.surface,
            'land_type': land.land_type.value if land.land_type else None,
            'urban_zone': land.urban_zone.value if hasattr(land.urban_zone, 'value') else land.urban_zone,
            'status': land.status.value,
            'satellite_verified': land.satellite_verified,
            'tax': {
                'id': tax.id,
                'tax_year': tax.tax_year,
                'tax_amount': tax.tax_amount,
                'total_amount': tax.total_amount,
                'is_payable': _is_payable,
                'payable_from': _payable_from,
                'status': tax.status.value,
                'paid': tax.status.value == 'paid'
            } if tax else None
        })
    if any_updates:
        db.session.commit()
    return jsonify({'lands': result}), 200

@blp.get('/lands/<int:land_id>')
@jwt_required()
def get_land(land_id):
    """Get land details with HATEOAS links"""
    from utils.hateoas import HATEOASBuilder
    
    user_id = get_current_user_id()
    user = User.query.get(user_id)
    
    land = Land.query.get(land_id)
    
    if not land:
        return jsonify({'error': ErrorMessages.NOT_FOUND}), 404
    
    # Check access: owner can view their own, staff can view in their commune, ministry admin can view all
    if user.role in [UserRole.MINISTRY_ADMIN]:
        pass  # Can view all
    elif user.role in [UserRole.MUNICIPAL_AGENT, UserRole.INSPECTOR, UserRole.MUNICIPAL_ADMIN]:
        if land.commune_id != user.commune_id:
            return jsonify({'error': ErrorMessages.ACCESS_DENIED}), 403
    else:  # Citizen/Business
        if land.owner_id != user_id:
            return jsonify({'error': ErrorMessages.ACCESS_DENIED}), 403
    
    tax = Tax.query.filter_by(land_id=land.id, tax_type=TaxType.TTNB).first()
    from datetime import date as _date
    _start = _date(int(tax.tax_year) + 1, 1, 1) if tax else None
    _is_payable = (_date.today() >= _start) if _start else False
    _payable_from = _start.isoformat() if _start else None
    if tax and tax.status != TaxStatus.PAID:
        new_penalty = TaxCalculator.compute_late_payment_penalty_for_year(
            tax_amount=tax.tax_amount,
            tax_year=tax.tax_year,
            section='TTNB'
        )
        if (tax.penalty_amount or 0.0) != new_penalty or (tax.total_amount or 0.0) != (tax.tax_amount + new_penalty):
            tax.penalty_amount = new_penalty
            tax.total_amount = tax.tax_amount + new_penalty
            db.session.commit()
    
    return jsonify({
        'id': land.id,
        'owner_id': land.owner_id,
        'commune_id': land.commune_id,
        'street_address': land.street_address,
        'city': land.city,
        'delegation': land.delegation,
        'post_code': land.post_code,
        'latitude': land.latitude,
        'longitude': land.longitude,
        'surface': land.surface,
        'land_type': land.land_type.value if land.land_type else None,
        'urban_zone': land.urban_zone.value if hasattr(land.urban_zone, 'value') else land.urban_zone,  # REQUIRED field per Décret 2017-396
        'is_exempt': land.is_exempt,
        'exemption_reason': land.exemption_reason,
        'status': land.status.value,
        'satellite_verified': land.satellite_verified,
        'created_at': land.created_at.isoformat() if land.created_at else None,
        'tax': {
            'id': tax.id,
            'tax_year': tax.tax_year,
            'base_amount': tax.base_amount,
            'rate_percent': tax.rate_percent,
            'tax_amount': tax.tax_amount,
            'penalty_amount': tax.penalty_amount,
            'total_amount': tax.total_amount,
            'is_payable': _is_payable,
            'payable_from': _payable_from,
            'status': tax.status.value
        } if tax else None
    })
    
    # Add HATEOAS links
    response['_links'] = HATEOASBuilder.add_land_links(land)
    
    return jsonify(response), 200

@blp.put('/lands/<int:land_id>')
@jwt_required()
@citizen_or_business_required
def update_land(land_id):
    """Update land (only owner can edit)"""
    user_id = get_current_user_id()
    
    land = Land.query.get(land_id)
    
    if not land:
        return jsonify({'error': ErrorMessages.NOT_FOUND}), 404
    
    # Ownership check
    if land.owner_id != user_id:
        return jsonify({'error': ErrorMessages.ACCESS_DENIED}), 403
    
    try:
        data = request.get_json()
    except Exception:
        return jsonify({'error': 'Invalid JSON'}), 400
    
    # Update allowed fields (including urban_zone)
    updatable_fields = [
        'street_address', 'city', 'delegation', 'post_code',
        'latitude', 'longitude', 'surface', 'land_type',
        'urban_zone', 'is_exempt', 'exemption_reason'
    ]
    
    # Validate urban_zone if being updated
    if 'urban_zone' in data and data['urban_zone'] not in VALID_URBAN_ZONES:
        return jsonify({
            'error': 'Invalid urban zone',
            'message': f'Urban zone must be one of: {list(VALID_URBAN_ZONES.keys())}',
            'valid_zones': VALID_URBAN_ZONES
        }), 400
    
    for field in updatable_fields:
        if field in data:
            setattr(land, field, data[field])
    
    # If address changed, recalculate coordinates
    if 'street_address' in data or 'city' in data:
        latitude, longitude = GeoLocator.geocode_address(
            data.get('street_address', land.street_address),
            data.get('city', land.city)
        )
        
        if latitude is None or longitude is None:
            if not data.get('latitude') or not data.get('longitude'):
                return jsonify({
                    'error': 'Address geocoding failed. Provide latitude/longitude.'
                }), 400
            land.latitude = float(data['latitude'])
            land.longitude = float(data['longitude'])
        else:
            land.latitude = latitude
            land.longitude = longitude
    
    db.session.commit()
    
    return jsonify({
        'message': 'Land updated successfully',
        'land_id': land.id,
        'updated_at': land.updated_at.isoformat()
    }), 200

@blp.get('/lands/<int:land_id>')
@jwt_required()
@citizen_or_business_required
def delete_land(land_id):
    """Delete land (only owner can delete, and only if no payments made)"""
    user_id = get_current_user_id()
    
    land = Land.query.get(land_id)
    
    if not land:
        return jsonify({'error': ErrorMessages.NOT_FOUND}), 404
    
    # Ownership check
    if land.owner_id != user_id:
        return jsonify({'error': ErrorMessages.ACCESS_DENIED}), 403
    
    # Check if any taxes paid
    paid_taxes = Tax.query.filter_by(land_id=land_id, status=TaxStatus.PAID).first()
    if paid_taxes:
        return jsonify({
            'error': 'Cannot delete land with paid taxes',
            'message': 'Lands with payment history cannot be deleted for audit purposes'
        }), 400
    
    # Delete land (cascade will delete taxes)
    db.session.delete(land)
    db.session.commit()
    
    return jsonify({
        'message': 'Land deleted successfully',
        'land_id': land_id
    }), 200

@blp.get('/lands/<int:land_id>/taxes')
@jwt_required()
def get_land_taxes(land_id):
    """Get taxes for a land"""
    land = Land.query.get(land_id)
    
    if not land:
        return jsonify({'error': ErrorMessages.NOT_FOUND}), 404
    
    taxes = Tax.query.filter_by(land_id=land_id, tax_type=TaxType.TTNB).all()
    any_updates = False
    for tax in taxes:
        if tax.status != TaxStatus.PAID:
            new_penalty = TaxCalculator.compute_late_payment_penalty_for_year(
                tax_amount=tax.tax_amount,
                tax_year=tax.tax_year,
                section='TTNB'
            )
            if (tax.penalty_amount or 0.0) != new_penalty or (tax.total_amount or 0.0) != (tax.tax_amount + new_penalty):
                tax.penalty_amount = new_penalty
                tax.total_amount = tax.tax_amount + new_penalty
                any_updates = True
    if any_updates:
        db.session.commit()
    
    from datetime import date as _date
    return jsonify({
        'land_id': land_id,
        'taxes': [{
            'id': tax.id,
            'tax_year': tax.tax_year,
            'base_amount': tax.base_amount,
            'rate_percent': tax.rate_percent,
            'tax_amount': tax.tax_amount,
            'penalty_amount': tax.penalty_amount,
            'total_amount': tax.total_amount,
            'is_payable': (_date.today() >= _date(int(tax.tax_year) + 1, 1, 1)),
            'payable_from': _date(int(tax.tax_year) + 1, 1, 1).isoformat(),
            'status': tax.status.value
        } for tax in taxes]
    }), 200

@blp.get('/my-taxes')
@jwt_required()
@citizen_or_business_required
def get_my_taxes():
    """Get all TTNB taxes for current user"""
    user_id = get_current_user_id()
    
    # Get all lands for user
    lands = Land.query.filter_by(owner_id=user_id).all()
    land_ids = [l.id for l in lands]
    
    # Get all TTNB taxes
    taxes = Tax.query.filter(
        Tax.land_id.in_(land_ids),
        Tax.tax_type == TaxType.TTNB
    ).all()
    # Apply dynamic penalty updates for unpaid taxes
    any_updates = False
    for tax in taxes:
        if tax.status != TaxStatus.PAID:
            new_penalty = TaxCalculator.compute_late_payment_penalty_for_year(
                tax_amount=tax.tax_amount,
                tax_year=tax.tax_year,
                section='TTNB'
            )
            if (tax.penalty_amount or 0.0) != new_penalty or (tax.total_amount or 0.0) != (tax.tax_amount + new_penalty):
                tax.penalty_amount = new_penalty
                tax.total_amount = tax.tax_amount + new_penalty
                any_updates = True
    if any_updates:
        db.session.commit()
    
    # Calculate totals
    total_tax = sum(t.tax_amount for t in taxes)
    total_penalties = sum(t.penalty_amount for t in taxes)
    total_due = sum(t.total_amount for t in taxes if t.status != TaxStatus.PAID)
    
    from datetime import date as _date
    return jsonify({
        'user_id': user_id,
        'summary': {
            'total_tax': round(total_tax, 2),
            'total_penalties': round(total_penalties, 2),
            'total_due': round(total_due, 2),
            'count': len(taxes)
        },
        'taxes': [{
            'id': tax.id,
            'land_id': tax.land_id,
            'tax_year': tax.tax_year,
            'tax_amount': tax.tax_amount,
            'penalty_amount': tax.penalty_amount,
            'total_amount': tax.total_amount,
            'is_payable': (_date.today() >= _date(int(tax.tax_year) + 1, 1, 1)),
            'payable_from': _date(int(tax.tax_year) + 1, 1, 1).isoformat(),
            'status': tax.status.value
        } for tax in taxes]
    }), 200
