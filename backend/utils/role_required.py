"""Role-based authorization decorators"""
from functools import wraps
from flask_jwt_extended import verify_jwt_in_request, get_jwt
from flask import jsonify
from models.user import UserRole

def role_required(*roles):
    """
    Decorator to require specific roles
    Usage: @role_required(UserRole.MUNICIPAL_ADMIN, UserRole.MUNICIPAL_AGENT)
    """
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            verify_jwt_in_request()
            claims = get_jwt()
            user_role = claims.get('role')
            
            # Convert role strings to UserRole enum values
            required_roles = [r.value if isinstance(r, UserRole) else r for r in roles]
            
            if user_role not in required_roles:
                return jsonify({
                    'error': 'Access denied',
                    'message': f'Required roles: {", ".join(required_roles)}'
                }), 403
            
            return fn(*args, **kwargs)
        return wrapper
    return decorator

def admin_required(fn):
    """Require municipal admin or ministry admin role"""
    return role_required(UserRole.MUNICIPAL_ADMIN, UserRole.MINISTRY_ADMIN)(fn)

def citizen_or_business_required(fn):
    """Require citizen or business role"""
    return role_required(UserRole.CITIZEN, UserRole.BUSINESS)(fn)

def municipal_staff_required(fn):
    """Require municipal agent, inspector, or similar"""
    return role_required(
        UserRole.MUNICIPAL_AGENT,
        UserRole.INSPECTOR,
        UserRole.FINANCE_OFFICER,
        UserRole.CONTENTIEUX_OFFICER,
        UserRole.URBANISM_OFFICER
    )(fn)

def finance_required(fn):
    """Require finance officer or elevated admin role"""
    return role_required(
        UserRole.FINANCE_OFFICER,
        UserRole.MUNICIPAL_ADMIN,
        UserRole.MINISTRY_ADMIN
    )(fn)

def contentieux_required(fn):
    """Require contentieux officer role"""
    return role_required(UserRole.CONTENTIEUX_OFFICER)(fn)

def inspector_required(fn):
    """Require inspector role"""
    return role_required(UserRole.INSPECTOR)(fn)

def agent_required(fn):
    """Require municipal agent role"""
    return role_required(UserRole.MUNICIPAL_AGENT)(fn)

def urbanism_required(fn):
    """Require urbanism/technical service role"""
    return role_required(UserRole.URBANISM_OFFICER)(fn)

def ministry_admin_required(fn):
    """Require ministry admin role (nation-wide access)"""
    def decorator(*args, **kwargs):
        verify_jwt_in_request()
        claims = get_jwt()
        user_role = claims.get('role')
        
        if user_role != UserRole.MINISTRY_ADMIN.value:
            return jsonify({
                'error': 'Access denied',
                'message': 'Ministry admin access required'
            }), 403
        
        return fn(*args, **kwargs)
    return wraps(fn)(decorator)

def municipal_admin_required(fn):
    """Require municipal admin role for specific municipality."""
    def decorator(*args, **kwargs):
        verify_jwt_in_request()
        claims = get_jwt()
        user_role = claims.get('role')
        user_commune_id = claims.get('commune_id')
        # Legacy ADMIN support removed; only MUNICIPAL_ADMIN is allowed
        allowed_roles = {
            UserRole.MUNICIPAL_ADMIN.value
        }
        
        if user_role not in allowed_roles:
            return jsonify({
                'error': 'Access denied',
                'message': 'Municipal admin access required'
            }), 403
        
        if not user_commune_id:
            return jsonify({
                'error': 'Invalid user',
                'message': 'Municipal admin must have commune_id'
            }), 400
        
        return fn(*args, **kwargs)
    return wraps(fn)(decorator)

def municipality_required(fn):
    """
    Allows access based on role and municipality binding.
    
    Rules:
    - MINISTRY_ADMIN: Can access all municipalities (commune_id=null)
    - MUNICIPAL_ADMIN, MUNICIPAL_AGENT, INSPECTOR, etc: Must have commune_id
    - CITIZEN, BUSINESS: Can be null (not bound to municipalities)
    
    This decorator ALLOWS access - data filtering is done in the endpoint logic.
    """
    def decorator(*args, **kwargs):
        verify_jwt_in_request()
        claims = get_jwt()
        user_role = claims.get('role')
        user_commune_id = claims.get('commune_id')
        
        # Ministry admin can access all communes (commune_id=null is expected)
        if user_role == UserRole.MINISTRY_ADMIN.value:
            return fn(*args, **kwargs)
        
        # Citizens and businesses are not bound to communes (can have null commune_id)
        if user_role in [UserRole.CITIZEN.value, UserRole.BUSINESS.value]:
            return fn(*args, **kwargs)
        
        # Municipal staff MUST have commune_id
        # (MUNICIPAL_ADMIN, MUNICIPAL_AGENT, INSPECTOR, FINANCE_OFFICER, CONTENTIEUX_OFFICER, URBANISM_OFFICER)
        if not user_commune_id:
            return jsonify({
                'error': 'Invalid user',
                'message': 'Municipal staff must belong to a municipality'
            }), 400
        
        return fn(*args, **kwargs)
    return wraps(fn)(decorator)
