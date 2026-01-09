"""Ministry Admin endpoints (nation-wide super admin)"""
from flask import jsonify, request
from flask_smorest import Blueprint
from flask_jwt_extended import jwt_required
from utils.jwt_helpers import get_current_user_id
from extensions.db import db
from models import User, UserRole, Commune, MunicipalReferencePrice, MunicipalServiceConfig
from utils.role_required import ministry_admin_required
from utils.validators import ErrorMessages, Validators
from datetime import datetime

ministry_bp = Blueprint('ministry', __name__, url_prefix='/api/v1/ministry')


@ministry_bp.get('/dashboard')
@ministry_admin_required
def get_dashboard():
    """Get nation-wide dashboard statistics"""
    from models import Property, Land, Tax, TaxStatus, Payment
    
    # Nation-wide statistics
    total_properties = Property.query.count()
    total_lands = Land.query.count()
    total_taxes = Tax.query.count()
    paid_taxes = Tax.query.filter_by(status=TaxStatus.PAID).count()
    total_payments = Payment.query.count()
    
    # Commune statistics
    communes = Commune.query.all()
    commune_stats = []
    for commune in communes:
        comm_properties = Property.query.filter_by(commune_id=commune.id).count()
        comm_taxes = Tax.query.join(Property).filter(Property.commune_id == commune.id).count()
        commune_stats.append({
            'commune_id': commune.id,
            'commune_name': commune.nom_municipalite_fr,
            'properties': comm_properties,
            'taxes': comm_taxes
        })
    
    return jsonify({
        'total_properties': total_properties,
        'total_lands': total_lands,
        'total_taxes': total_taxes,
        'paid_taxes': paid_taxes,
        'payment_rate': (paid_taxes / total_taxes * 100) if total_taxes > 0 else 0,
        'total_payments': total_payments,
        'commune_statistics': commune_stats
    }), 200


# ============================================================================
# MUNICIPALITY MANAGEMENT
# ============================================================================

@ministry_bp.get('/municipalities')
@jwt_required()
@ministry_admin_required
def list_municipalities():
    """List all municipalities"""
    from models import Property, Land, Tax, TaxStatus
    
    communes = Commune.query.order_by(Commune.nom_municipalite_fr.asc()).all()
    
    municipalities = []
    for commune in communes:
        properties_count = Property.query.filter_by(commune_id=commune.id).count()
        lands_count = Land.query.filter_by(commune_id=commune.id).count()
        taxes_count = Tax.query.join(Property).filter(
            Property.commune_id == commune.id
        ).count()
        
        # Find municipal admin for this commune
        admin = User.query.filter_by(
            commune_id=commune.id,
            role=UserRole.MUNICIPAL_ADMIN
        ).first()
        
        municipalities.append({
            'id': commune.id,
            'code_municipalite': commune.code_municipalite,
            'nom_municipalite_fr': commune.nom_municipalite_fr,
            'nom_gouvernorat_fr': commune.nom_gouvernorat_fr,
            'properties_count': properties_count,
            'lands_count': lands_count,
            'taxes_count': taxes_count,
            'admin_name': f"{admin.first_name} {admin.last_name}" if admin else None,
            'admin_email': admin.email if admin else None,
        })
    
    return jsonify({'municipalities': municipalities}), 200


@ministry_bp.get('/municipalities/<int:commune_id>')
@ministry_admin_required
def get_municipality(commune_id):
    """Get detailed information about a municipality"""
    commune = Commune.query.get(commune_id)
    if not commune:
        return jsonify({'error': ErrorMessages.NOT_FOUND}), 404
    
    from models import Property, Land, Tax, TaxStatus
    
    properties = Property.query.filter_by(commune_id=commune.id).count()
    lands = Land.query.filter_by(commune_id=commune.id).count()
    taxes = Tax.query.join(Property).filter(Property.commune_id == commune.id).count()
    paid_taxes = Tax.query.join(Property).filter(
        (Property.commune_id == commune.id) & (Tax.status == TaxStatus.PAID)
    ).count()
    
    # Get reference prices for all categories
    ref_prices = MunicipalReferencePrice.query.filter_by(commune_id=commune.id).all()
    
    # Get services
    services = MunicipalServiceConfig.query.filter_by(commune_id=commune.id).all()
    services_payload = [{
        'id': s.id,
        'name': s.service_name,
        'code': s.service_code,
        'locality_name': s.locality_name,
        'available': s.is_available
    } for s in services]
    locality_breakdown = {}
    for svc in services:
        key = svc.locality_name or '__all__'
        locality_breakdown.setdefault(key, 0)
        locality_breakdown[key] += 1
    
    return jsonify({
        'id': commune.id,
        'code': commune.code_municipalite,
        'name': commune.nom_municipalite_fr,
        'gouvernorat': commune.nom_gouvernorat_fr,
        'type': commune.type_mun_fr,
        'statistics': {
            'total_properties': properties,
            'total_lands': lands,
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
        'services': services_payload,
        'service_scope_summary': {
            'total': len(services_payload),
            'by_scope': [
                {
                    'locality': locality if locality != '__all__' else None,
                    'count': count
                } for locality, count in locality_breakdown.items()
            ]
        }
    }), 200


# ============================================================================
# MUNICIPAL ADMIN MANAGEMENT
# ============================================================================

@ministry_bp.post('/municipal-admins')
@ministry_admin_required
def create_municipal_admin():
    """Create a new municipal admin for a commune"""
    data = request.get_json()
    
    # Validate required fields
    required = ['username', 'email', 'password', 'commune_id']
    if not all(data.get(f) for f in required):
        return jsonify({'error': 'Missing required fields'}), 400
    
    # Verify commune exists
    commune = Commune.query.get(data['commune_id'])
    if not commune:
        return jsonify({'error': 'Commune not found'}), 404
    
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
    user = User(
        username=data['username'],
        email=data['email'],
        role=UserRole.MUNICIPAL_ADMIN,
        commune_id=data['commune_id'],
        first_name=data.get('first_name'),
        last_name=data.get('last_name'),
        is_active=True
    )
    user.set_password(data['password'])
    
    db.session.add(user)
    db.session.commit()
    
    return jsonify({
        'message': 'Municipal admin created successfully',
        'user_id': user.id,
        'username': user.username,
        'commune_id': user.commune_id,
        'commune_name': commune.nom_municipalite_fr
    }), 201


@ministry_bp.get('/municipal-admins')
@ministry_admin_required
def list_municipal_admins():
    """List all municipal admins"""
    admins = User.query.filter_by(role=UserRole.MUNICIPAL_ADMIN).all()
    
    admin_list = []
    for admin in admins:
        commune = Commune.query.get(admin.commune_id) if admin.commune_id else None
        admin_list.append({
            'id': admin.id,
            'username': admin.username,
            'email': admin.email,
            'first_name': admin.first_name,
            'last_name': admin.last_name,
            'commune_name': commune.nom_municipalite_fr if commune else None,
            'commune_id': admin.commune_id,
            'is_active': admin.is_active,
            'created_at': admin.created_at.isoformat() if admin.created_at else None
        })
    
    return jsonify({'municipal_admins': admin_list}), 200


@ministry_bp.patch('/municipal-admins/<int:user_id>/status')
@ministry_admin_required
def update_admin_status(user_id):
    """Enable or disable a municipal admin"""
    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': ErrorMessages.NOT_FOUND}), 404
    
    if user.role != UserRole.MUNICIPAL_ADMIN:
        return jsonify({'error': 'User is not a municipal admin'}), 400
    
    data = request.get_json()
    if 'is_active' in data:
        user.is_active = bool(data['is_active'])
        db.session.commit()
    
    return jsonify({
        'message': f'Admin {("activated" if user.is_active else "deactivated")}',
        'user_id': user.id,
        'is_active': user.is_active
    }), 200


# ============================================================================
# AUDIT & REPORTS
# ============================================================================

@ministry_bp.get('/audit-log')
@ministry_admin_required
def get_audit_log():
    """Get all administrative actions (reference price changes, service configs)"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 100, type=int)
    
    # Get all reference price changes
    ref_price_logs = db.session.query(
        MunicipalReferencePrice.id.label('id'),
        MunicipalReferencePrice.set_at.label('timestamp'),
        User.username.label('username'),
        MunicipalReferencePrice.commune_id.label('commune_id'),
        db.literal('reference_price_change').label('action_type')
    ).join(
        User, MunicipalReferencePrice.set_by_user_id == User.id, isouter=True
    )
    
    # Get all service configuration changes
    service_logs = db.session.query(
        MunicipalServiceConfig.id.label('id'),
        MunicipalServiceConfig.configured_at.label('timestamp'),
        User.username.label('username'),
        MunicipalServiceConfig.commune_id.label('commune_id'),
        db.literal('service_config_change').label('action_type')
    ).join(
        User, MunicipalServiceConfig.configured_by_user_id == User.id, isouter=True
    )
    
    # Combine and order
    combined = ref_price_logs.union_all(service_logs).order_by(
        db.desc(db.text('timestamp'))
    ).paginate(page=page, per_page=per_page)
    
    return jsonify({
        'total': combined.total,
        'page': page,
        'audit_log': [{
            'timestamp': log.timestamp.isoformat() if log.timestamp else None,
            'action_type': log.action_type,
            'user': log.username,
            'commune_id': log.commune_id
        } for log in combined.items]
    }), 200


# ============================================================================
# REFERENCE PRICE BOUNDS (Ministry sets legal min/max per category)
# ============================================================================

@ministry_bp.get('/reference-price-bounds')
@ministry_admin_required
def get_reference_price_bounds():
    """Get legal min/max bounds for all TIB categories (Code de la Fiscalité Locale 2025)"""
    bounds = [
        {'category': 1, 'label': '≤100 m²', 'legal_min': 100, 'legal_max': 178},
        {'category': 2, 'label': '100-200 m²', 'legal_min': 163, 'legal_max': 238},
        {'category': 3, 'label': '200-400 m²', 'legal_min': 217, 'legal_max': 297},
        {'category': 4, 'label': '>400 m²', 'legal_min': 271, 'legal_max': 356},
    ]
    
    return jsonify({'bounds': bounds}), 200


@ministry_bp.put('/reference-price-bounds/<int:category>')
@ministry_admin_required
def update_reference_price_bounds(category):
    """Update legal min/max bounds for a TIB category (requires ministry authority)"""
    if category not in [1, 2, 3, 4]:
        return jsonify({'error': 'Invalid category. Must be 1, 2, 3, or 4'}), 400
    
    data = request.get_json()
    
    if 'legal_min' not in data or 'legal_max' not in data:
        return jsonify({'error': 'Both legal_min and legal_max required'}), 400
    
    legal_min = float(data['legal_min'])
    legal_max = float(data['legal_max'])
    
    if legal_min >= legal_max:
        return jsonify({'error': 'legal_min must be less than legal_max'}), 400
    
    if legal_min < 0:
        return jsonify({'error': 'Prices cannot be negative'}), 400
    
    user_id = get_current_user_id()
    
    # Update all municipalities' reference prices for this category
    ref_prices = MunicipalReferencePrice.query.filter_by(tib_category=category).all()
    
    updated_count = 0
    for rp in ref_prices:
        rp.legal_min = legal_min
        rp.legal_max = legal_max
        
        # Clamp existing reference price to new bounds
        if rp.reference_price_per_m2 < legal_min:
            rp.reference_price_per_m2 = legal_min
        elif rp.reference_price_per_m2 > legal_max:
            rp.reference_price_per_m2 = legal_max
        
        rp.set_by_user_id = user_id
        rp.set_at = datetime.utcnow()
        updated_count += 1
    
    db.session.commit()
    
    return jsonify({
        'message': f'Updated bounds for category {category}',
        'category': category,
        'legal_min': legal_min,
        'legal_max': legal_max,
        'municipalities_affected': updated_count
    }), 200


@ministry_bp.get('/reports/reference-prices')
@ministry_admin_required
def get_reference_prices_report():
    """Get all reference prices by municipality and category"""
    communes = Commune.query.all()
    
    report = []
    for commune in communes:
        ref_prices = MunicipalReferencePrice.query.filter_by(commune_id=commune.id).all()
        report.append({
            'commune_id': commune.id,
            'commune_name': commune.nom_municipalite_fr,
            'gouvernorat': commune.nom_gouvernorat_fr,
            'reference_prices': [{
                'category': rp.tib_category,
                'legal_min': rp.legal_min,
                'legal_max': rp.legal_max,
                'current_price': rp.reference_price_per_m2,
                'last_updated': rp.set_at.isoformat() if rp.set_at else None,
                'set_by': User.query.get(rp.set_by_user_id).username if rp.set_by_user_id else None
            } for rp in ref_prices]
        })
    
    return jsonify({'report': report}), 200


@ministry_bp.get('/reports/revenue')
@ministry_admin_required
def get_revenue_report():
    """Get total revenue by municipality"""
    from models import Tax, TaxStatus, Property
    
    communes = Commune.query.all()
    
    report = []
    total_revenue = 0
    
    for commune in communes:
        comm_taxes = db.session.query(Tax).join(
            Property, Tax.property_id == Property.id
        ).filter(
            (Property.commune_id == commune.id) & (Tax.status == TaxStatus.PAID)
        ).all()
        
        revenue = sum(t.total_amount for t in comm_taxes if t.total_amount)
        total_revenue += revenue
        
        report.append({
            'commune_id': commune.id,
            'commune_name': commune.nom_municipalite_fr,
            'revenue': round(revenue, 2),
            'tax_count': len(comm_taxes)
        })
    
    # Sort by revenue descending
    report = sorted(report, key=lambda x: x['revenue'], reverse=True)
    
    return jsonify({
        'total_revenue': round(total_revenue, 2),
        'revenue_by_municipality': report
    }), 200
