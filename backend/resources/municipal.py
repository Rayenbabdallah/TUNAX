"""Municipal Admin endpoints (per-municipality management)"""
from flask import jsonify, request
from flask_smorest import Blueprint
from flask_jwt_extended import jwt_required
from utils.jwt_helpers import get_current_user_id
from extensions.db import db
from models import (User, UserRole, Commune, MunicipalReferencePrice, 
                    MunicipalServiceConfig, DocumentRequirement, Property, Land, Tax, TaxStatus)
from utils.role_required import municipal_admin_required, municipality_required
from utils.validators import ErrorMessages, Validators
from datetime import datetime
from utils.calculator import TaxCalculator

municipal_bp = Blueprint('municipal', __name__, url_prefix='/api/v1/municipal')


def get_user_municipality():
    """Get current user's municipality"""
    user_id = get_current_user_id()
    user = User.query.get(user_id)
    if not user or not user.commune_id:
        return None
    return user.commune_id


# ============================================================================
# PROFILE
# ============================================================================

@municipal_bp.get('/me')
@jwt_required()
@municipality_required
def get_municipal_profile():
    """Get current municipal admin profile and municipality info"""
    user_id = get_current_user_id()
    user = User.query.get(user_id)
    
    if not user or not user.commune_id:
        return jsonify({'error': 'Municipality not assigned'}), 404
    
    commune = Commune.query.get(user.commune_id)
    
    return jsonify({
        'user': {
            'id': user.id,
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'role': user.role.value
        },
        'municipality': {
            'id': commune.id,
            'code': commune.code_municipalite,
            'name': commune.nom_municipalite_fr,
            'governorate': commune.nom_gouvernorat_fr,
            'type': commune.type_mun_fr
        }
    }), 200

# ============================================================================
# DASHBOARD
# ============================================================================

@municipal_bp.get('/dashboard')
@jwt_required()
@municipality_required
def get_dashboard():
    """Get municipality dashboard"""
    user_id = get_current_user_id()
    user = User.query.get(user_id)
    commune_id = user.commune_id
    
    # Statistics for this municipality only
    properties = Property.query.filter_by(commune_id=commune_id).count()
    lands = Land.query.filter_by(commune_id=commune_id).count()
    
    taxes = Tax.query.join(Property).filter(Property.commune_id == commune_id).count()
    paid_taxes = Tax.query.join(Property).filter(
        (Property.commune_id == commune_id) & (Tax.status == TaxStatus.PAID)
    ).count()
    
    # Reference prices
    ref_prices = MunicipalReferencePrice.query.filter_by(commune_id=commune_id).all()
    
    # Services
    services = MunicipalServiceConfig.query.filter_by(commune_id=commune_id).all()
    available_services = len([s for s in services if s.is_available])
    
    return jsonify({
        'municipality': {
            'id': user.commune_id,
            'name': Commune.query.get(user.commune_id).nom_municipalite_fr
        },
        'statistics': {
            'properties': properties,
            'lands': lands,
            'total_taxes': taxes,
            'paid_taxes': paid_taxes,
            'collection_rate': (paid_taxes / taxes * 100) if taxes > 0 else 0
        },
        'reference_prices': [{
            'category': rp.tib_category,
            'legal_min': rp.legal_min,
            'legal_max': rp.legal_max,
            'current_price': rp.reference_price_per_m2
        } for rp in ref_prices],
        'services': {
            'total': len(services),
            'available': available_services,
            'list': [{
                'id': s.id,
                'name': s.service_name,
                'code': s.service_code,
                'available': s.is_available
            } for s in services]
        }
    }), 200


# ============================================================================
# REFERENCE PRICES MANAGEMENT (TIB)
# ============================================================================

@municipal_bp.get('/reference-prices')
@jwt_required()
@municipality_required
def get_reference_prices():
    """Get all reference prices for current municipality"""
    user_id = get_current_user_id()
    user = User.query.get(user_id)
    
    ref_prices = MunicipalReferencePrice.query.filter_by(
        commune_id=user.commune_id
    ).order_by(MunicipalReferencePrice.tib_category).all()
    
    return jsonify({
        'commune_id': user.commune_id,
        'reference_prices': [{
            'id': rp.id,
            'category': rp.tib_category,
            'category_description': f"{'≤ 100 m²' if rp.tib_category == 1 else '100-200 m²' if rp.tib_category == 2 else '200-400 m²' if rp.tib_category == 3 else '> 400 m²'}",
            'legal_min': rp.legal_min,
            'legal_max': rp.legal_max,
            'current_price': rp.reference_price_per_m2,
            'last_updated': rp.set_at.isoformat() if rp.set_at else None
        } for rp in ref_prices]
    }), 200


@municipal_bp.put('/reference-prices/<int:category>')
@jwt_required()
@municipal_admin_required
def update_reference_price(category):
    """Update reference price for a category"""
    if category not in [1, 2, 3, 4]:
        return jsonify({'error': 'Invalid category (must be 1-4)'}), 400
    
    user_id = get_current_user_id()
    user = User.query.get(user_id)
    
    data = request.get_json()
    if not data.get('reference_price_per_m2'):
        return jsonify({'error': 'reference_price_per_m2 required'}), 400
    
    price = float(data['reference_price_per_m2'])
    
    # Get the reference price record
    ref_price = MunicipalReferencePrice.query.filter_by(
        commune_id=user.commune_id,
        tib_category=category
    ).first()
    
    if not ref_price:
        return jsonify({'error': 'Reference price not found'}), 404
    
    # Validate within legal bounds
    if not (ref_price.legal_min <= price <= ref_price.legal_max):
        return jsonify({
            'error': 'Price outside legal bounds',
            'legal_range': f"{ref_price.legal_min} - {ref_price.legal_max} TND/m²"
        }), 400
    
    # Update
    ref_price.reference_price_per_m2 = price
    ref_price.set_by_user_id = user_id
    ref_price.set_at = datetime.utcnow()
    db.session.commit()
    
    return jsonify({
        'message': 'Reference price updated',
        'category': category,
        'new_price': price,
        'updated_at': ref_price.set_at.isoformat()
    }), 200


# ============================================================================
# SERVICES MANAGEMENT
# ============================================================================

@municipal_bp.get('/services')
@jwt_required()
@municipality_required
def get_services():
    """Get all services for current municipality"""
    user_id = get_current_user_id()
    user = User.query.get(user_id)
    
    services = MunicipalServiceConfig.query.filter_by(
        commune_id=user.commune_id
    ).all()
    
    available_count = len([s for s in services if s.is_available])
    
    return jsonify({
        'commune_id': user.commune_id,
        'total_services': len(services),
        'available_services': available_count,
        'services': [{
            'id': s.id,
            'name': s.service_name,
            'code': s.service_code,
            'locality_name': s.locality_name,
            'available': s.is_available,
            'configured_at': s.configured_at.isoformat() if s.configured_at else None
        } for s in services]
    }), 200


@municipal_bp.post('/services')
@jwt_required()
@municipal_admin_required
def add_service():
    """Add a new service to municipality"""
    user_id = get_current_user_id()
    user = User.query.get(user_id)
    
    data = request.get_json()
    if not data.get('service_name') or not data.get('service_code'):
        return jsonify({'error': 'service_name and service_code required'}), 400
    
    locality_name = (data.get('locality_name') or '').strip() or None
    
    # Check for duplicate
    existing = MunicipalServiceConfig.query.filter_by(
        commune_id=user.commune_id,
        service_code=data['service_code'],
        locality_name=locality_name
    ).first()
    
    if existing:
        return jsonify({'error': 'Service already exists'}), 409
    
    service = MunicipalServiceConfig(
        commune_id=user.commune_id,
        locality_name=locality_name,
        service_name=data['service_name'],
        service_code=data['service_code'],
        is_available=data.get('is_available', True),
        configured_by_user_id=user_id,
        configured_at=datetime.utcnow()
    )
    
    db.session.add(service)
    db.session.commit()
    
    return jsonify({
        'message': 'Service added',
        'service_id': service.id,
        'service_name': service.service_name,
        'service_code': service.service_code,
        'locality_name': service.locality_name
    }), 201


@municipal_bp.patch('/services/<int:service_id>')
@jwt_required()
@municipal_admin_required
def update_service(service_id):
    """Update service availability"""
    user_id = get_current_user_id()
    user = User.query.get(user_id)
    
    service = MunicipalServiceConfig.query.filter_by(
        id=service_id,
        commune_id=user.commune_id
    ).first()
    
    if not service:
        return jsonify({'error': ErrorMessages.NOT_FOUND}), 404
    
    data = request.get_json()
    changed = False
    if 'is_available' in data:
        service.is_available = bool(data['is_available'])
        changed = True
    if 'locality_name' in data:
        requested_locality = (data.get('locality_name') or '').strip() or None
        if requested_locality != service.locality_name:
            duplicate = MunicipalServiceConfig.query.filter(
                MunicipalServiceConfig.commune_id == user.commune_id,
                MunicipalServiceConfig.service_code == service.service_code,
                MunicipalServiceConfig.locality_name == requested_locality,
                MunicipalServiceConfig.id != service.id
            ).first()
            if duplicate:
                return jsonify({'error': 'Service already exists for this locality'}), 409
            service.locality_name = requested_locality
            changed = True
    if changed:
        service.configured_at = datetime.utcnow()
        db.session.commit()
    
    return jsonify({
        'message': 'Service updated',
        'service_id': service.id,
        'is_available': service.is_available,
        'locality_name': service.locality_name
    }), 200


@municipal_bp.delete('/services/<int:service_id>')
@jwt_required()
@municipal_admin_required
def delete_service(service_id):
    """Delete a service"""
    user_id = get_current_user_id()
    user = User.query.get(user_id)
    
    service = MunicipalServiceConfig.query.filter_by(
        id=service_id,
        commune_id=user.commune_id
    ).first()
    
    if not service:
        return jsonify({'error': ErrorMessages.NOT_FOUND}), 404
    
    db.session.delete(service)
    db.session.commit()
    
    return jsonify({
        'message': 'Service deleted',
        'service_id': service_id
    }), 200


# ============================================================================
# DATA VIEWS (scoped to municipality)
# ============================================================================

@municipal_bp.get('/properties')
@jwt_required()
@municipality_required
def get_properties():
    """Get all properties in municipality"""
    user_id = get_current_user_id()
    user = User.query.get(user_id)
    
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)
    
    properties = Property.query.filter_by(commune_id=user.commune_id).paginate(
        page=page, per_page=per_page
    )
    
    return jsonify({
        'total': properties.total,
        'page': page,
        'properties': [{
            'id': p.id,
            'owner_id': p.owner_id,
            'address': f"{p.street_address}, {p.city}",
            'surface_couverte': p.surface_couverte,
            'reference_price_per_m2': p.reference_price_per_m2,
            'status': p.status.value if p.status else None
        } for p in properties.items]
    }), 200


@municipal_bp.get('/lands')
@jwt_required()
@municipality_required
def get_lands():
    """Get all lands in municipality"""
    user_id = get_current_user_id()
    user = User.query.get(user_id)
    
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)
    
    lands = Land.query.filter_by(commune_id=user.commune_id).paginate(
        page=page, per_page=per_page
    )
    
    return jsonify({
        'total': lands.total,
        'page': page,
        'lands': [{
            'id': l.id,
            'owner_id': l.owner_id,
            'address': f"{l.street_address}, {l.city}",
            'surface': l.surface,
            'urban_zone': l.urban_zone,
            'status': l.status.value if l.status else None
        } for l in lands.items]
    }), 200


@municipal_bp.get('/users')
@jwt_required()
@municipality_required
def get_users():
    """Get all users (citizens, businesses, staff) in municipality"""
    user_id = get_current_user_id()
    user = User.query.get(user_id)
    
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)
    role_filter = request.args.get('role', None)
    
    query = User.query.filter_by(commune_id=user.commune_id)
    
    if role_filter:
        try:
            role = UserRole[role_filter.upper()]
            query = query.filter_by(role=role)
        except KeyError:
            return jsonify({'error': 'Invalid role'}), 400
    
    users = query.paginate(page=page, per_page=per_page)
    
    return jsonify({
        'total': users.total,
        'page': page,
        'users': [{
            'id': u.id,
            'username': u.username,
            'email': u.email,
            'role': u.role.value,
            'is_active': u.is_active
        } for u in users.items]
    }), 200


# ============================================================================
# STAFF MANAGEMENT (mirror of /api/admin/staff but under /api/municipal)
# ============================================================================


@municipal_bp.post('/staff')
@jwt_required()
@municipal_admin_required
def create_municipal_staff():
    """Create a new staff member in this municipality (municipal admin)"""
    data = request.get_json()
    user_id = get_current_user_id()
    admin = User.query.get(user_id)
    commune_id = admin.commune_id

    # Validate required fields
    if not data.get('username') or not data.get('email') or not data.get('password') or not data.get('role'):
        return jsonify({'error': 'Missing required fields'}), 400

    # Municipality admin can only create these staff roles
    allowed_roles = [
        UserRole.MUNICIPAL_AGENT.value,
        UserRole.INSPECTOR.value,
        UserRole.FINANCE_OFFICER.value,
        UserRole.CONTENTIEUX_OFFICER.value,
        UserRole.URBANISM_OFFICER.value
    ]

    if data['role'] not in allowed_roles:
        return jsonify({
            'error': 'Invalid role for municipality staff',
            'allowed_roles': allowed_roles
        }), 400

    # Check duplicates
    if User.query.filter_by(username=data['username']).first():
        return jsonify({'error': ErrorMessages.DUPLICATE_USERNAME}), 409

    if User.query.filter_by(email=data['email']).first():
        return jsonify({'error': ErrorMessages.DUPLICATE_EMAIL}), 409

    # Validate password
    is_valid, msg = Validators.validate_password(data['password'])
    if not is_valid:
        return jsonify({'error': msg}), 400

    # Create staff user for this municipality
    user = User(
        username=data['username'],
        email=data['email'],
        first_name=data.get('first_name'),
        last_name=data.get('last_name'),
        phone=data.get('phone'),
        commune_id=commune_id,
        role=UserRole[data['role'].upper()],
        is_active=True
    )
    user.set_password(data['password'])

    db.session.add(user)
    db.session.commit()

    commune = Commune.query.get(commune_id)

    return jsonify({
        'message': 'Staff member created successfully',
        'user_id': user.id,
        'username': user.username,
        'role': user.role.value,
        'commune_id': commune_id,
        'commune_name': commune.nom_municipalite_fr if commune else None
    }), 201


@municipal_bp.get('/staff')
@jwt_required()
@municipal_admin_required
def list_municipal_staff():
    """List all staff in this municipality"""
    user_id = get_current_user_id()
    admin = User.query.get(user_id)
    commune_id = admin.commune_id

    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    role_filter = request.args.get('role', None)

    # Only get staff for this municipality
    query = User.query.filter_by(commune_id=commune_id)

    # Exclude other admins and citizens/businesses
    excluded_roles = [UserRole.MINISTRY_ADMIN, UserRole.CITIZEN, UserRole.BUSINESS, UserRole.MUNICIPAL_ADMIN]
    query = query.filter(User.role.notin_(excluded_roles))

    if role_filter:
        try:
            role = UserRole[role_filter.upper()]
            query = query.filter_by(role=role)
        except KeyError:
            return jsonify({'error': 'Invalid role filter'}), 400

    users = query.paginate(page=page, per_page=per_page)

    return jsonify({
        'total': users.total,
        'page': page,
        'per_page': per_page,
        'pages': users.pages,
        'staff': [{
            'id': u.id,
            'username': u.username,
            'email': u.email,
            'role': u.role.value,
            'first_name': u.first_name,
            'last_name': u.last_name,
            'is_active': u.is_active,
            'created_at': u.created_at.isoformat() if u.created_at else None
        } for u in users.items]
    }), 200


@municipal_bp.patch('/staff/<int:staff_id>')
@jwt_required()
@municipal_admin_required
def update_municipal_staff(staff_id):
    """Update staff member status or details"""
    user_id = get_current_user_id()
    admin = User.query.get(user_id)
    commune_id = admin.commune_id

    staff = User.query.get(staff_id)

    if not staff:
        return jsonify({'error': ErrorMessages.NOT_FOUND}), 404

    # Verify staff belongs to this municipality
    if staff.commune_id != commune_id:
        return jsonify({'error': ErrorMessages.ACCESS_DENIED}), 403

    # Cannot modify other admins
    if staff.role in [UserRole.MINISTRY_ADMIN, UserRole.MUNICIPAL_ADMIN]:
        return jsonify({'error': 'Cannot modify admin accounts'}), 403

    data = request.get_json()

    if 'is_active' in data:
        staff.is_active = bool(data['is_active'])

    if 'phone' in data:
        staff.phone = data['phone']

    if 'last_name' in data:
        staff.last_name = data['last_name']

    if 'first_name' in data:
        staff.first_name = data['first_name']

    db.session.commit()

    return jsonify({
        'message': 'Staff updated successfully',
        'user_id': staff.id,
        'username': staff.username,
        'is_active': staff.is_active
    }), 200


@municipal_bp.delete('/staff/<int:staff_id>')
@jwt_required()
@municipal_admin_required
def delete_municipal_staff(staff_id):
    """Delete/deactivate a staff member"""
    user_id = get_current_user_id()
    admin = User.query.get(user_id)
    commune_id = admin.commune_id

    staff = User.query.get(staff_id)

    if not staff:
        return jsonify({'error': ErrorMessages.NOT_FOUND}), 404

    # Verify staff belongs to this municipality
    if staff.commune_id != commune_id:
        return jsonify({'error': ErrorMessages.ACCESS_DENIED}), 403

    # Cannot delete other admins
    if staff.role in [UserRole.MINISTRY_ADMIN, UserRole.MUNICIPAL_ADMIN]:
        return jsonify({'error': 'Cannot delete admin accounts'}), 403

    # Soft delete by deactivating
    staff.is_active = False
    db.session.commit()

    return jsonify({
        'message': 'Staff member deactivated',
        'user_id': staff.id
    }), 200


@municipal_bp.post('/staff')
@jwt_required()
@municipal_admin_required
def create_staff():
    """Create new municipal staff member"""
    user_id = get_current_user_id()
    user = User.query.get(user_id)
    
    data = request.get_json()
    
    # Validate required fields
    required = ['username', 'email', 'password', 'role']
    if not all(data.get(f) for f in required):
        return jsonify({'error': 'Missing required fields'}), 400
    
    # Validate role
    try:
        role = UserRole[data['role'].upper()]
    except KeyError:
        return jsonify({'error': 'Invalid role'}), 400
    
    # Only allow municipal staff roles
    allowed_roles = [
        UserRole.MUNICIPAL_AGENT,
        UserRole.INSPECTOR,
        UserRole.FINANCE_OFFICER,
        UserRole.CONTENTIEUX_OFFICER,
        UserRole.URBANISM_OFFICER
    ]
    
    if role not in allowed_roles:
        return jsonify({'error': f'Invalid role for municipal staff'}), 400
    
    # Check for duplicates
    if User.query.filter_by(username=data['username']).first():
        return jsonify({'error': ErrorMessages.DUPLICATE_USERNAME}), 409
    if User.query.filter_by(email=data['email']).first():
        return jsonify({'error': ErrorMessages.DUPLICATE_EMAIL}), 409
    
    # Validate password
    is_valid, msg = Validators.validate_password(data['password'])
    if not is_valid:
        return jsonify({'error': msg}), 400
    
    # Create user
    new_user = User(
        username=data['username'],
        email=data['email'],
        role=role,
        commune_id=user.commune_id,
        first_name=data.get('first_name'),
        last_name=data.get('last_name'),
        phone=data.get('phone'),
        is_active=True
    )
    new_user.set_password(data['password'])
    
    db.session.add(new_user)
    db.session.commit()
    
    return jsonify({
        'message': 'Staff member created',
        'user_id': new_user.id,
        'username': new_user.username,
        'role': new_user.role.value
    }), 201


@municipal_bp.patch('/staff/<int:staff_id>')
@jwt_required()
@municipal_admin_required
def update_staff(staff_id):
    """Update staff member"""
    user_id = get_current_user_id()
    user = User.query.get(user_id)
    
    staff = User.query.filter_by(
        id=staff_id,
        commune_id=user.commune_id
    ).first()
    
    if not staff:
        return jsonify({'error': ErrorMessages.NOT_FOUND}), 404
    
    data = request.get_json()
    
    if 'is_active' in data:
        staff.is_active = bool(data['is_active'])
    if 'first_name' in data:
        staff.first_name = data['first_name']
    if 'last_name' in data:
        staff.last_name = data['last_name']
    if 'phone' in data:
        staff.phone = data['phone']
    
    db.session.commit()
    
    return jsonify({
        'message': 'Staff updated',
        'user_id': staff.id
    }), 200


@municipal_bp.delete('/staff/<int:staff_id>')
@jwt_required()
@municipal_admin_required
def delete_staff(staff_id):
    """Remove staff member"""
    user_id = get_current_user_id()
    user = User.query.get(user_id)
    
    staff = User.query.filter_by(
        id=staff_id,
        commune_id=user.commune_id
    ).first()
    
    if not staff:
        return jsonify({'error': ErrorMessages.NOT_FOUND}), 404
    
    if staff.id == user_id:
        return jsonify({'error': 'Cannot delete yourself'}), 400
    
    db.session.delete(staff)
    db.session.commit()
    
    return jsonify({
        'message': 'Staff deleted',
        'user_id': staff_id
    }), 200


# ============================================================================
# TAXES SUMMARY
# ============================================================================

@municipal_bp.get('/taxes/summary')
@jwt_required()
@municipality_required
def get_taxes_summary():
    """Get tax collection summary for municipality"""
    user_id = get_current_user_id()
    user = User.query.get(user_id)
    
    # Get all taxes for properties in this municipality
    taxes = db.session.query(Tax).join(
        Property, Tax.property_id == Property.id
    ).filter(Property.commune_id == user.commune_id).all()
    # Recompute penalties for unpaid taxes (1.25%/mo from Jan 1 of year+2)
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

    total_amount = sum(t.total_amount for t in taxes if t.total_amount)
    paid_amount = sum(t.total_amount for t in [t for t in taxes if t.status == TaxStatus.PAID] if t.total_amount)
    pending_amount = total_amount - paid_amount
    
    return jsonify({
        'total_taxes': len(taxes),
        'total_amount': round(total_amount, 2),
        'paid_amount': round(paid_amount, 2),
        'pending_amount': round(pending_amount, 2),
        'collection_rate': round((paid_amount / total_amount * 100), 2) if total_amount > 0 else 0,
        'by_status': {
            'calculated': len([t for t in taxes if t.status == TaxStatus.CALCULATED]),
            'paid': len([t for t in taxes if t.status == TaxStatus.PAID]),
            'overdue': len([t for t in taxes if t.status == TaxStatus.OVERDUE])
        }
    }), 200


# ============================================================================
# DOCUMENT REQUIREMENTS MANAGEMENT
# ============================================================================

@municipal_bp.get('/document-requirements')
@jwt_required()
@municipality_required
def get_document_requirements():
    """Get all document requirements for current municipality"""
    user_id = get_current_user_id()
    user = User.query.get(user_id)
    
    requirements = DocumentRequirement.query.filter_by(
        commune_id=user.commune_id
    ).order_by(DocumentRequirement.declaration_type, DocumentRequirement.display_order).all()
    
    # Group by declaration type
    by_type = {}
    for req in requirements:
        if req.declaration_type not in by_type:
            by_type[req.declaration_type] = []
        by_type[req.declaration_type].append({
            'id': req.id,
            'document_code': req.document_code,
            'document_name': req.document_name,
            'description': req.description,
            'is_mandatory': req.is_mandatory,
            'display_order': req.display_order
        })
    
    return jsonify({
        'commune_id': user.commune_id,
        'total_requirements': len(requirements),
        'by_type': by_type
    }), 200


@municipal_bp.post('/document-requirements')
@jwt_required()
@municipal_admin_required
def create_document_requirement():
    """Create a new document requirement"""
    user_id = get_current_user_id()
    user = User.query.get(user_id)
    
    data = request.get_json()
    
    # Validate required fields
    if not data.get('document_name') or not data.get('document_code'):
        return jsonify({'error': 'document_name and document_code required'}), 400
    
    if data.get('declaration_type') not in ['property', 'land', 'all']:
        return jsonify({'error': 'declaration_type must be property, land, or all'}), 400
    
    # Check for duplicate
    existing = DocumentRequirement.query.filter_by(
        commune_id=user.commune_id,
        declaration_type=data['declaration_type'],
        document_code=data['document_code']
    ).first()
    
    if existing:
        return jsonify({'error': 'Document requirement already exists'}), 409
    
    req = DocumentRequirement(
        commune_id=user.commune_id,
        declaration_type=data['declaration_type'],
        document_name=data['document_name'],
        document_code=data['document_code'],
        description=data.get('description'),
        is_mandatory=data.get('is_mandatory', True),
        display_order=data.get('display_order', 0),
        created_by_user_id=user_id,
        updated_by_user_id=user_id
    )
    
    db.session.add(req)
    db.session.commit()
    
    return jsonify({
        'message': 'Document requirement created',
        'requirement_id': req.id,
        'document_code': req.document_code,
        'document_name': req.document_name
    }), 201


@municipal_bp.put('/document-requirements/<int:requirement_id>')
@jwt_required()
@municipal_admin_required
def update_document_requirement(requirement_id):
    """Update a document requirement"""
    user_id = get_current_user_id()
    user = User.query.get(user_id)
    
    req = DocumentRequirement.query.filter_by(
        id=requirement_id,
        commune_id=user.commune_id
    ).first()
    
    if not req:
        return jsonify({'error': 'Document requirement not found'}), 404
    
    data = request.get_json()
    
    # Update fields
    if 'document_name' in data:
        req.document_name = data['document_name']
    if 'description' in data:
        req.description = data['description']
    if 'is_mandatory' in data:
        req.is_mandatory = data['is_mandatory']
    if 'display_order' in data:
        req.display_order = data['display_order']
    
    req.updated_by_user_id = user_id
    req.updated_at = datetime.utcnow()
    
    db.session.commit()
    
    return jsonify({
        'message': 'Document requirement updated',
        'requirement_id': req.id,
        'document_code': req.document_code,
        'document_name': req.document_name
    }), 200


@municipal_bp.delete('/document-requirements/<int:requirement_id>')
@jwt_required()
@municipal_admin_required
def delete_document_requirement(requirement_id):
    """Delete a document requirement"""
    user_id = get_current_user_id()
    user = User.query.get(user_id)
    
    req = DocumentRequirement.query.filter_by(
        id=requirement_id,
        commune_id=user.commune_id
    ).first()
    
    if not req:
        return jsonify({'error': 'Document requirement not found'}), 404
    
    document_code = req.document_code
    db.session.delete(req)
    db.session.commit()
    
    return jsonify({
        'message': 'Document requirement deleted',
        'document_code': document_code
    }), 200
