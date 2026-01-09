"""TIB (Taxe sur les Immeubles Bâtis) management routes (flask-smorest)"""
from flask import jsonify, request
from flask_smorest import Blueprint
from flask_jwt_extended import jwt_required
from utils.jwt_helpers import get_current_user_id
from extensions.db import db
from models.user import User, UserRole
from models.property import Property, PropertyStatus
from models.tax import Tax, TaxType, TaxStatus
from models.payment import Payment
from models import Commune, Declaration, DeclarationType
from schemas.tax_permit import PropertyCreateSchema, PropertySchema, TaxResultSchema
from utils.calculator import TaxCalculator
from utils.geo import GeoLocator
from utils.role_required import citizen_or_business_required, role_required, municipality_required
from utils.validators import Validators, ErrorMessages
from datetime import datetime

blp = Blueprint('tib', 'tib', url_prefix='/api/v1/tib')

@blp.post('/properties')
@jwt_required()
@citizen_or_business_required
@blp.arguments(PropertyCreateSchema)
@blp.response(201, PropertySchema)
def declare_property(data):
    """Declare a new property (TIB) in any municipality
    
    Create a new property declaration for Built Property Tax (Taxe sur les Immeubles Bâtis).
    Citizens and businesses can declare properties in any municipality across Tunisia.
    
    ---
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - commune_id
            - street_address
            - city
            - surface_couverte
            - construction_year
            - urban_zone
            - affectation
          properties:
            commune_id:
              type: integer
              description: ID of the municipality where the property is located
            address_mode:
              type: string
              enum: [villa, residence, other]
              description: Type of address structure (villa, residence, or other)
            street_name:
              type: string
              description: Street name (required if address_mode is villa/residence)
            villa_number:
              type: string
              description: Villa number (required if address_mode is villa)
            residence_name:
              type: string
              description: Residence name (required if address_mode is residence)
            apartment_number:
              type: string
              description: Apartment number (required if address_mode is residence)
            locality:
              type: string
              description: Locality/neighborhood name
            street_address:
              type: string
              description: Full street address (auto-composed if address_mode provided)
            city:
              type: string
              description: City name (auto-filled from commune if not provided)
            delegation:
              type: string
              description: Delegation/district
            latitude:
              type: number
              format: float
              description: GPS latitude (auto-geocoded if not provided)
            longitude:
              type: number
              format: float
              description: GPS longitude (auto-geocoded if not provided)
            surface_couverte:
              type: number
              format: float
              description: Covered surface area in m²
            construction_year:
              type: integer
              description: Year of construction
            urban_zone:
              type: string
              enum: [urban, suburban, rural]
              description: Urban zone classification
            affectation:
              type: string
              enum: [residential, commercial, industrial, mixed]
              description: Property usage type
            reference_price_per_m2:
              type: number
              format: float
              description: Reference price per m² (optional, defaults to commune rate)
    responses:
      201:
        description: Property declared successfully with calculated tax
        schema:
          type: object
          properties:
            id:
              type: integer
              description: Property ID
            declaration_id:
              type: integer
              description: Associated declaration ID
            street_address:
              type: string
            city:
              type: string
            surface_couverte:
              type: number
            construction_year:
              type: integer
            urban_zone:
              type: string
            affectation:
              type: string
            latitude:
              type: number
            longitude:
              type: number
            tax:
              type: object
              description: Calculated tax details
              properties:
                id:
                  type: integer
                amount:
                  type: number
                year:
                  type: integer
                status:
                  type: string
      400:
        description: Invalid input or missing commune_id
      404:
        description: Commune not found
    """
    user_id = get_current_user_id()
    user = User.query.get(user_id)
    
    # REQUIRED: commune_id MUST be provided by citizen/business (via property data)
    # Citizens/businesses are NOT bound to a commune - they can declare in any municipality
    commune_id = data.get('commune_id')
    if not commune_id:
        return jsonify({
            'error': 'Commune required',
            'message': 'Property must specify commune_id indicating which municipality it is in.'
        }), 400
    
    # Verify commune exists
    commune = Commune.query.get(commune_id)
    if not commune:
        return jsonify({'error': f'Commune with ID {commune_id} not found'}), 404
    
    # If structured address provided, compose the canonical address fields
    if data.get('address_mode') in ['villa', 'residence']:
        # Ensure street name and either villa/apartment details exist
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
        # Override address inputs expected by schema and storage
        data['street_address'] = composed
        # Use commune official name for city
        data['city'] = commune.nom_municipalite_fr
        # Store locality as delegation when provided
        if locality:
            data['delegation'] = locality

    # Determine coordinates: prefer provided lat/lng, else geocode
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
            'message': 'Property coordinates must be within Tunisia (lat: 32-37.5, lon: 7-12)'
        }), 400
    
    # Create property with commune_id
    property_obj = Property(
        owner_id=user_id,
        commune_id=commune_id,
        street_address=data['street_address'],
        city=data['city'],
        delegation=data.get('delegation'),
        post_code=data.get('post_code'),
        latitude=latitude,
        longitude=longitude,
        surface_couverte=data['surface_couverte'],
        surface_totale=data.get('surface_totale'),
        affectation=data['affectation'],
        nb_floors=data.get('nb_floors'),
        nb_rooms=data.get('nb_rooms'),
        construction_year=data.get('construction_year'),
        # Use reference_price_per_m2 instead of total reference_price
        reference_price_per_m2=data.get('reference_price_per_m2'),
        tax_rate_category=data.get('tax_rate_category'),
        is_exempt=data.get('is_exempt', False),
        exemption_reason=data.get('exemption_reason'),
        status=PropertyStatus.DECLARED
    )
    
    db.session.add(property_obj)
    try:
        db.session.flush()
    except Exception as e:
        db.session.rollback()
        if 'unique_property_per_owner_commune' in str(e):
            return jsonify({'error': 'Property already exists', 'message': 'You have already declared a property with this address in this commune'}), 409
        return jsonify({'error': 'Database error', 'message': str(e)}), 500

    # Create declaration record for document workflow (supports attachments/review)
    declaration = Declaration(
        owner_id=user_id,
        commune_id=commune_id,
        declaration_type=DeclarationType.PROPERTY.value,
        reference_id=property_obj.id,
        status="submitted",
    )
    db.session.add(declaration)
    db.session.flush()
    # Calculate TIB using new legally-correct formula
    calc_result = TaxCalculator.calculate_tib(property_obj)
    
    if 'error' in calc_result:
        db.session.rollback()
        return jsonify({'error': calc_result['error'], 'message': calc_result.get('message')}), 400
    
    tax = Tax(
        property_id=property_obj.id,
        tax_type=TaxType.TIB,
        tax_year=datetime.now().year,
        base_amount=calc_result.get('base_amount'),
        rate_percent=calc_result.get('rate_percent'),
        tax_amount=calc_result['tax_amount'],
        total_amount=calc_result['total_amount'],
        status=TaxStatus.CALCULATED
    )
    
    db.session.add(tax)
    db.session.commit()
    
    return jsonify({
        'message': 'Property declared successfully with legally-correct TIB calculation',
        'property_id': property_obj.id,
        'commune_id': commune_id,
        'declaration_id': declaration.id,
        'tax_id': tax.id,
        'tax_calculation': {
            'assiette': calc_result.get('base_amount'),
            'service_rate_percent': calc_result.get('rate_percent'),
            'tib_amount': calc_result['tax_amount'],
        }
    }), 201

@blp.get('/properties')
@jwt_required()
@municipality_required
def get_properties():
    """Get properties (filtered based on user role and municipality access)"""
    user_id = get_current_user_id()
    user = User.query.get(user_id)
    
    # Access control based on role:
    # CITIZEN/BUSINESS: Can see ONLY their own properties (across all municipalities)
    # MUNICIPAL_AGENT/INSPECTOR/FINANCE_OFFICER: Can see ALL properties in their municipality
    # MINISTRY_ADMIN: Can see ALL properties nation-wide
    
    if user.role in [UserRole.CITIZEN, UserRole.BUSINESS]:
        # Citizens/businesses see only THEIR OWN properties
        properties = Property.query.filter_by(owner_id=user_id).all()
    elif user.role in [UserRole.MUNICIPAL_AGENT, UserRole.INSPECTOR, UserRole.FINANCE_OFFICER, UserRole.CONTENTIEUX_OFFICER, UserRole.URBANISM_OFFICER]:
        # Municipal staff see all properties in their municipality
        properties = Property.query.filter_by(commune_id=user.commune_id).all()
    elif user.role == UserRole.MUNICIPAL_ADMIN:
        # Municipal admin sees all properties in their municipality
        properties = Property.query.filter_by(commune_id=user.commune_id).all()
    elif user.role == UserRole.MINISTRY_ADMIN:
        # Ministry admin sees all properties nation-wide
        properties = Property.query.all()
    else:
        properties = []
    
    result = []
    any_updates = False
    for prop in properties:
        tax = Tax.query.filter_by(property_id=prop.id, tax_type=TaxType.TIB).first()
        if tax and tax.status != TaxStatus.PAID:
            # Apply dynamic penalty policy: 1.25%/mo from Jan 1 of (year+2)
            new_penalty = TaxCalculator.compute_late_payment_penalty_for_year(
                tax_amount=tax.tax_amount,
                tax_year=tax.tax_year,
                section='TIB'
            )
            if (tax.penalty_amount or 0.0) != new_penalty or (tax.total_amount or 0.0) != (tax.tax_amount + new_penalty):
                tax.penalty_amount = new_penalty
                tax.total_amount = tax.tax_amount + new_penalty
                any_updates = True
        # Payability flags (N+1 start)
        from datetime import date as _date
        _start = _date(int(tax.tax_year) + 1, 1, 1) if tax else None
        _is_payable = (_date.today() >= _start) if _start else False
        _payable_from = _start.isoformat() if _start else None
        # Get first declaration for this property
        declaration = Declaration.query.filter_by(reference_id=prop.id, declaration_type=DeclarationType.PROPERTY.value).first()
        result.append({
            'id': prop.id,
            'owner_id': prop.owner_id,
            'commune_id': prop.commune_id,
            'street_address': prop.street_address,
            'city': prop.city,
            'surface_couverte': prop.surface_couverte,
            'affectation': prop.affectation.value if prop.affectation else None,
            'status': prop.status.value,
            'satellite_verified': prop.satellite_verified,
            'declaration_id': declaration.id if declaration else None,
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
    return jsonify({'properties': result}), 200

@blp.get('/properties/<int:property_id>')
@jwt_required()
def get_property(property_id):
    """Get property details with HATEOAS links"""
    from utils.hateoas import HATEOASBuilder
    
    user_id = get_current_user_id()
    user = User.query.get(user_id)
    
    prop = Property.query.get(property_id)
    
    if not prop:
        return jsonify({'error': ErrorMessages.NOT_FOUND}), 404
    
    # Check access: owner can view their own, staff can view in their commune, ministry admin can view all
    if user.role in [UserRole.MINISTRY_ADMIN]:
        pass  # Can view all
    elif user.role in [UserRole.MUNICIPAL_AGENT, UserRole.INSPECTOR, UserRole.MUNICIPAL_ADMIN]:
        if prop.commune_id != user.commune_id:
            return jsonify({'error': ErrorMessages.ACCESS_DENIED}), 403
    else:  # Citizen/Business
        if prop.owner_id != user_id:
            return jsonify({'error': ErrorMessages.ACCESS_DENIED}), 403
    
    tax = Tax.query.filter_by(property_id=prop.id, tax_type=TaxType.TIB).first()
    # Payability flags
    from datetime import date as _date
    _start = _date(int(tax.tax_year) + 1, 1, 1) if tax else None
    _is_payable = (_date.today() >= _start) if _start else False
    _payable_from = _start.isoformat() if _start else None
    if tax and tax.status != TaxStatus.PAID:
      new_penalty = TaxCalculator.compute_late_payment_penalty_for_year(
        tax_amount=tax.tax_amount,
        tax_year=tax.tax_year,
        section='TIB'
      )
      if (tax.penalty_amount or 0.0) != new_penalty or (tax.total_amount or 0.0) != (tax.tax_amount + new_penalty):
        tax.penalty_amount = new_penalty
        tax.total_amount = tax.tax_amount + new_penalty
        db.session.commit()
    
    response = {
      'id': prop.id,
      'owner_id': prop.owner_id,
      'commune_id': prop.commune_id,
      'street_address': prop.street_address,
      'city': prop.city,
      'delegation': prop.delegation,
      'post_code': prop.post_code,
      'latitude': prop.latitude,
      'longitude': prop.longitude,
      'surface_couverte': prop.surface_couverte,
      'surface_totale': prop.surface_totale,
      'affectation': prop.affectation.value if prop.affectation else None,
      'nb_floors': prop.nb_floors,
      'nb_rooms': prop.nb_rooms,
      'construction_year': prop.construction_year,
      'reference_price_per_m2': prop.reference_price_per_m2,
      'is_exempt': prop.is_exempt,
      'exemption_reason': prop.exemption_reason,
      'status': prop.status.value,
      'satellite_verified': prop.satellite_verified,
      'created_at': prop.created_at.isoformat() if prop.created_at else None,
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
    }
    # Add HATEOAS links
    response['_links'] = HATEOASBuilder.add_property_links(prop)
    return jsonify(response), 200

@blp.put('/properties/<int:property_id>')
@jwt_required()
@citizen_or_business_required
def update_property(property_id):
    """Update property (only owner can edit)"""
    user_id = get_current_user_id()
    
    prop = Property.query.get(property_id)
    
    if not prop:
        return jsonify({'error': ErrorMessages.NOT_FOUND}), 404
    
    # Ownership check
    if prop.owner_id != user_id:
        return jsonify({'error': ErrorMessages.ACCESS_DENIED}), 403
    
    try:
        data = request.get_json()
    except Exception:
        return jsonify({'error': 'Invalid JSON'}), 400
    
    # Update allowed fields
    updatable_fields = [
        'street_address', 'city', 'delegation', 'post_code',
        'latitude', 'longitude', 'surface_couverte', 'surface_totale',
        'affectation', 'nb_floors', 'nb_rooms', 'construction_year',
        'reference_price_per_m2', 'is_exempt', 'exemption_reason'
    ]
    
    for field in updatable_fields:
        if field in data:
            value = data[field]
            # Handle enum fields
            if field == 'affectation' and isinstance(value, str):
                from models.property import PropertyAffectation
                try:
                    value = PropertyAffectation(value)
                except ValueError:
                    pass  # Keep as string if not valid enum
            setattr(prop, field, value)
    
    # If address changed, try to geocode (fallback to manual lat/lon if failure)
    if 'street_address' in data or 'city' in data:
        try:
          from utils.external_apis import NominatimClient, ExternalAPIError
          geocoder = NominatimClient()
          query = f"{data.get('street_address', prop.street_address)}, {data.get('city', prop.city)}"
          result = geocoder.geocode(query=query, limit=1)
          if result.get('results') and len(result['results']) > 0:
            coords = result['results'][0]
            prop.latitude = float(coords.get('lat', 0))
            prop.longitude = float(coords.get('lon', 0))
        except ExternalAPIError:
          # If geocoding fails, allow manual entry if provided
          if data.get('latitude') and data.get('longitude'):
            prop.latitude = float(data['latitude'])
            prop.longitude = float(data['longitude'])
          else:
            return jsonify({
              'error': 'Geocoding failed; manual coordinates required',
              'required_fields': ['latitude', 'longitude']
            }), 400
        except Exception:
          # Any other failure: require manual coordinates
          if data.get('latitude') and data.get('longitude'):
            prop.latitude = float(data['latitude'])
            prop.longitude = float(data['longitude'])
          else:
            return jsonify({
              'error': 'Address update requires coordinates when geocoder unavailable',
              'required_fields': ['latitude', 'longitude']
            }), 400
    
    db.session.commit()
    
    return jsonify({
        'message': 'Property updated successfully',
        'property_id': prop.id,
        'updated_at': prop.updated_at.isoformat()
    }), 200

@blp.get('/properties/<int:property_id>')
@jwt_required()
@citizen_or_business_required
def delete_property(property_id):
    """Delete property (only owner can delete, and only if no payments made)"""
    user_id = get_current_user_id()
    
    prop = Property.query.get(property_id)
    
    if not prop:
        return jsonify({'error': ErrorMessages.NOT_FOUND}), 404
    
    # Ownership check
    if prop.owner_id != user_id:
        return jsonify({'error': ErrorMessages.ACCESS_DENIED}), 403
    
    # Check if any taxes paid
    paid_taxes = Tax.query.filter_by(property_id=property_id, status=TaxStatus.PAID).first()
    if paid_taxes:
        return jsonify({
            'error': 'Cannot delete property with paid taxes',
            'message': 'Properties with payment history cannot be deleted for audit purposes'
        }), 400
    
    # Delete property (cascade will delete taxes)
    db.session.delete(prop)
    db.session.commit()
    
    return jsonify({
        'message': 'Property deleted successfully',
        'property_id': property_id
    }), 200

@blp.get('/properties/<int:property_id>/taxes')
@jwt_required()
def get_property_taxes(property_id):
    """Get taxes for a property with HATEOAS links"""
    from utils.hateoas import HATEOASBuilder
    
    prop = Property.query.get(property_id)
    
    if not prop:
        return jsonify({'error': ErrorMessages.NOT_FOUND}), 404
    
    taxes = Tax.query.filter_by(property_id=property_id, tax_type=TaxType.TIB).all()
    any_updates = False
    for tax in taxes:
      if tax.status != TaxStatus.PAID:
        new_penalty = TaxCalculator.compute_late_payment_penalty_for_year(
          tax_amount=tax.tax_amount,
          tax_year=tax.tax_year,
          section='TIB'
        )
        if (tax.penalty_amount or 0.0) != new_penalty or (tax.total_amount or 0.0) != (tax.tax_amount + new_penalty):
          tax.penalty_amount = new_penalty
          tax.total_amount = tax.tax_amount + new_penalty
          any_updates = True
    if any_updates:
      db.session.commit()
    
    from datetime import date as _date
    # Build response with HATEOAS links
    response_data = {
        'property_id': property_id,
        'taxes': []
    }

    for tax in taxes:
        tax_data = {
            'id': tax.id,
            'tax_year': tax.tax_year,
            'base_amount': tax.base_amount,
            'rate_percent': tax.rate_percent,
            'tax_amount': tax.tax_amount,
            'penalty_amount': tax.penalty_amount,
            'total_amount': tax.total_amount,
            'is_payable': (_date.today() >= _date(int(tax.tax_year) + 1, 1, 1)),
            'payable_from': _date(int(tax.tax_year) + 1, 1, 1).isoformat(),
            'status': tax.status.value,
            '_links': HATEOASBuilder.add_tax_links(tax, resource_type="property")
        }
        response_data['taxes'].append(tax_data)

    response_data['_links'] = {
        'self': {
            'href': f'/api/v1/tib/properties/{property_id}/taxes',
            'method': 'GET'
        },
        'property': {
            'href': f'/api/v1/tib/properties/{property_id}',
            'method': 'GET',
            'description': 'View property details'
        }
    }

    return jsonify(response_data), 200

@blp.get('/my-taxes')
@jwt_required()
@citizen_or_business_required
def get_my_taxes():
    """Get all taxes for current user"""
    user_id = get_current_user_id()
    
    # Get all properties for user
    properties = Property.query.filter_by(owner_id=user_id).all()
    property_ids = [p.id for p in properties]
    
    # Get all TIB taxes
    taxes = Tax.query.filter(
        Tax.property_id.in_(property_ids),
        Tax.tax_type == TaxType.TIB
    ).all()
    # Apply dynamic penalty updates for unpaid taxes
    any_updates = False
    for tax in taxes:
      if tax.status != TaxStatus.PAID:
        new_penalty = TaxCalculator.compute_late_payment_penalty_for_year(
          tax_amount=tax.tax_amount,
          tax_year=tax.tax_year,
          section='TIB'
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
            'property_id': tax.property_id,
            'tax_year': tax.tax_year,
            'tax_amount': tax.tax_amount,
            'penalty_amount': tax.penalty_amount,
        'total_amount': tax.total_amount,
        'is_payable': (_date.today() >= _date(int(tax.tax_year) + 1, 1, 1)),
        'payable_from': _date(int(tax.tax_year) + 1, 1, 1).isoformat(),
            'status': tax.status.value
        } for tax in taxes]
    }), 200
