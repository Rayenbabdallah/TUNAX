"""Municipality Admin management routes"""
from flask import jsonify, request
from flask_smorest import Blueprint
from flask_jwt_extended import jwt_required
from utils.jwt_helpers import get_current_user_id
from extensions.db import db
from models.user import User, UserRole
from models import Commune
from utils.role_required import municipal_admin_required
from utils.validators import Validators, ErrorMessages
from marshmallow import ValidationError, Schema, fields

blp = Blueprint('admin', 'admin', url_prefix='/api/v1/admin')


# Schemas
class CreateStaffSchema(Schema):
    """Schema for creating staff members"""
    username = fields.Str(required=True)
    email = fields.Email(required=True)
    password = fields.Str(required=True)
    role = fields.Str(required=True)
    first_name = fields.Str(allow_none=True)
    last_name = fields.Str(allow_none=True)
    phone = fields.Str(allow_none=True)


class UpdateStaffSchema(Schema):
    """Schema for updating staff members"""
    is_active = fields.Bool(allow_none=True)
    phone = fields.Str(allow_none=True)
    last_name = fields.Str(allow_none=True)
    first_name = fields.Str(allow_none=True)

@blp.get('/dashboard')
@blp.response(200)
@jwt_required()
@municipal_admin_required
def get_dashboard():
    """Get municipality admin dashboard
    
    Retrieve comprehensive statistics for the municipality managed by the current admin.
    Includes property counts, tax collection rates, and revenue data.
    """
    from models import Property, Land, Tax, TaxStatus, Payment
    
    user_id = get_current_user_id()
    user = User.query.get(user_id)
    commune_id = user.commune_id
    
    # Municipality-specific statistics
    properties = Property.query.filter_by(commune_id=commune_id).count()
    lands = Land.query.filter_by(commune_id=commune_id).count()
    
    taxes = Tax.query.join(Property).filter(Property.commune_id == commune_id).count()
    paid_taxes = Tax.query.join(Property).filter(
        (Property.commune_id == commune_id) & (Tax.status == TaxStatus.PAID)
    ).count()
    
    # Revenue for this municipality
    revenue = db.session.query(db.func.sum(Payment.amount)).join(
        Tax, Payment.tax_id == Tax.id
    ).join(
        Property, Tax.property_id == Property.id
    ).filter(
        (Property.commune_id == commune_id) & (Tax.status == TaxStatus.PAID)
    ).scalar() or 0
    
    commune = Commune.query.get(commune_id)
    
    return jsonify({
        'municipality': {
            'id': commune_id,
            'name': commune.nom_municipalite_fr if commune else None
        },
        'statistics': {
            'properties': properties,
            'lands': lands,
            'total_taxes': taxes,
            'paid_taxes': paid_taxes,
            'collection_rate': (paid_taxes / taxes * 100) if taxes > 0 else 0,
            'revenue': round(float(revenue), 2)
        }
    }), 200

@blp.post('/staff')
@blp.arguments(CreateStaffSchema, location="json")
@blp.response(201)
@jwt_required()
@municipal_admin_required
def create_staff(data):
    """Create a new staff member in this municipality
    
    Municipal admins can create staff members (agents, inspectors, officers) for their municipality.
    Staff members are automatically assigned to the admin's municipality.
    """
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
        commune_id=commune_id,  # Staff tied to admin's municipality
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

@blp.get('/staff')
@blp.response(200)
@jwt_required()
@municipal_admin_required
def list_staff():
    """List all staff in this municipality
    
    Retrieve paginated list of staff members for the admin's municipality.
    Supports filtering by role and pagination.
    """
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

@blp.patch('/staff/<int:staff_id>')
@blp.arguments(UpdateStaffSchema, location="json")
@blp.response(200)
@jwt_required()
@municipal_admin_required
def update_staff(data, staff_id):
    # Get staff and verify ownership first
    user_id = get_current_user_id()
    admin = User.query.get(user_id)
    commune_id = admin.commune_id

    staff = User.query.get(staff_id)

    if not staff:
        return jsonify({'error': ErrorMessages.NOT_FOUND}), 404

    # Verify staff belongs to this municipality
    if staff.commune_id != commune_id:
        return jsonify({'error': ErrorMessages.ACCESS_DENIED}), 403

    # Apply updates
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

@blp.delete('/staff/<int:staff_id>')
@blp.response(200)
@jwt_required()
@municipal_admin_required
def delete_staff(staff_id):
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

