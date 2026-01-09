"""Authentication routes (flask-smorest)"""
from flask import jsonify, request
from flask_smorest import Blueprint
from flask_jwt_extended import create_access_token, create_refresh_token, jwt_required, get_jwt
from utils.jwt_helpers import get_current_user_id
from werkzeug.security import generate_password_hash
from sqlalchemy import or_
from datetime import datetime

from extensions.db import db
from extensions.jwt import add_token_to_blacklist
from extensions.limiter import limiter
from models.user import User, UserRole
from models import Commune
from schemas.auth import UserRegisterCitizenSchema, UserRegisterBusinessSchema, LoginSchema, TokenSchema
from utils.validators import Validators, ErrorMessages
from marshmallow import ValidationError

blp = Blueprint('auth', 'auth', url_prefix='/api/v1/auth')


def _redirect_path(role: UserRole) -> str:
    """Map roles to dashboard paths served by the frontend."""
    mapping = {
        UserRole.CITIZEN: '/dashboards/citizen/',
        UserRole.BUSINESS: '/dashboards/business/',
        UserRole.MUNICIPAL_AGENT: '/dashboards/agent/',
        UserRole.INSPECTOR: '/dashboards/inspector/',
        UserRole.FINANCE_OFFICER: '/dashboards/finance/',
        UserRole.CONTENTIEUX_OFFICER: '/dashboards/contentieux/',
        UserRole.URBANISM_OFFICER: '/dashboards/urbanism/',
        UserRole.MUNICIPAL_ADMIN: '/dashboards/admin/',
        UserRole.MINISTRY_ADMIN: '/dashboards/ministry/',
    }
    return mapping.get(role, '/common_login/index.html')

@blp.post('/register-citizen')
@blp.arguments(UserRegisterCitizenSchema)
@blp.response(201, TokenSchema)
@limiter.limit('5 per minute')
def register_citizen(data):
    """Register a new citizen (optionally with municipality)"""
    from flask import jsonify
    
    # Check if user already exists
    if User.query.filter_by(username=data['username']).first():
        return jsonify({'error': ErrorMessages.DUPLICATE_USERNAME}), 409
    
    if User.query.filter_by(email=data['email']).first():
        return jsonify({'error': ErrorMessages.DUPLICATE_EMAIL}), 409
    
    if data.get('cin') and User.query.filter_by(cin=data['cin']).first():
        return jsonify({'error': ErrorMessages.DUPLICATE_CIN}), 409
    
    # Validate password strength
    is_valid, msg = Validators.validate_password(data['password'])
    if not is_valid:
        return {'error': msg}, 400
    
    # Citizens NOT bound to municipality - can own properties/lands in multiple communes
    # commune_id parameter is IGNORED for citizens
    # Each property/land specifies its own commune_id
    
    # Create new citizen (NO commune binding)
    user = User(
        username=data['username'],
        email=data['email'],
        first_name=data.get('first_name'),
        last_name=data.get('last_name'),
        phone=data.get('phone'),
        cin=data.get('cin'),
        commune_id=None,  # Citizens are NOT bound to a specific commune
        role=UserRole.CITIZEN,
        is_active=True
    )
    user.set_password(data['password'])
    
    db.session.add(user)
    db.session.commit()
    
    user_identity = str(user.id)
    additional_claims = {
        'role': user.role.value,
    }
    if user.commune_id:
        additional_claims['commune_id'] = user.commune_id
    
    access_token = create_access_token(identity=user_identity, additional_claims=additional_claims)
    refresh_token = create_refresh_token(identity=user_identity)
    response = {
        'access_token': access_token,
        'refresh_token': refresh_token,
        'role': user.role.value,
        'redirect_to': _redirect_path(user.role)
    }
    if user.commune_id:
        response['commune_id'] = user.commune_id
    
    return response

@blp.post('/register-business')
@blp.arguments(UserRegisterBusinessSchema)
@blp.response(201, TokenSchema)
@limiter.limit('5 per minute')
def register_business(data):
    """Register a new business (optionally with municipality)"""
    from flask import jsonify
    
    # Check if user already exists
    if User.query.filter_by(username=data['username']).first():
        return jsonify({'error': ErrorMessages.DUPLICATE_USERNAME}), 409
    
    if User.query.filter_by(email=data['email']).first():
        return jsonify({'error': ErrorMessages.DUPLICATE_EMAIL}), 409
    
    # Validate password strength
    is_valid, msg = Validators.validate_password(data['password'])
    if not is_valid:
        return {'error': msg}, 400
    
    # Businesses NOT bound to municipality - can own properties/lands in multiple communes
    # commune_id parameter is IGNORED for businesses
    # Each property/land specifies its own commune_id
    
    # Create new business (NO commune binding)
    user = User(
        username=data['username'],
        email=data['email'],
        first_name=data.get('first_name'),
        last_name=data.get('last_name'),
        phone=data.get('phone'),
        business_name=data.get('business_name'),
        business_registration=data.get('business_registration'),
        commune_id=None,  # Businesses are NOT bound to a specific commune
        role=UserRole.BUSINESS,
        is_active=True
    )
    user.set_password(data['password'])
    
    db.session.add(user)
    db.session.commit()
    
    user_identity = str(user.id)
    additional_claims = {
        'role': user.role.value,
    }
    if user.commune_id:
        additional_claims['commune_id'] = user.commune_id
    
    access_token = create_access_token(identity=user_identity, additional_claims=additional_claims)
    refresh_token = create_refresh_token(identity=user_identity)
    response = {
        'access_token': access_token,
        'refresh_token': refresh_token,
        'role': user.role.value,
        'redirect_to': _redirect_path(user.role)
    }
    if user.commune_id:
        response['commune_id'] = user.commune_id
    
    return response

@blp.post('/login')
@blp.arguments(LoginSchema)
@blp.response(200, TokenSchema)
@limiter.limit('5 per minute')
def login(data):
    """Login user with 2FA support"""
    if not data.get('username') or not data.get('password'):
        return {'error': 'Username/email and password required'}, 400

    # Accept either username or email to match common UX expectations
    identifier = data['username']
    user = User.query.filter(
        or_(User.username == identifier, User.email == identifier)
    ).first()
    
    if not user or not user.check_password(data['password']):
        return {'error': ErrorMessages.INVALID_CREDENTIALS}, 401
    
    if not user.is_active:
        return {'error': 'User account is inactive'}, 403
    
    # Check if 2FA is enabled
    from models.two_factor import TwoFactorAuth
    two_fa = TwoFactorAuth.query.filter_by(user_id=user.id, is_enabled=True).first()
    
    if two_fa:
        # 2FA is enabled - require token
        token_2fa = data.get('totp_token')
        backup_code = data.get('backup_code')
        
        if not token_2fa and not backup_code:
            return {
                'error': '2FA token required',
                'requires_2fa': True,
                'user_id': user.id
            }, 403
        
        # Verify 2FA
        if token_2fa:
            if not two_fa.verify_token(token_2fa):
                return {'error': 'Invalid 2FA token'}, 401
        elif backup_code:
            if not two_fa.use_backup_code(backup_code):
                return {'error': 'Invalid backup code'}, 401
            db.session.commit()
        
        # Update last used
        two_fa.last_used = datetime.utcnow()
        db.session.commit()
    
    # Create tokens
    user_identity = str(user.id)
    additional_claims = {
        'role': user.role.value,
    }
    if user.commune_id:
        additional_claims['commune_id'] = user.commune_id
    
    access_token = create_access_token(
        identity=user_identity,
        additional_claims=additional_claims
    )
    refresh_token = create_refresh_token(identity=user_identity)
    response = {
        'access_token': access_token,
        'refresh_token': refresh_token,
        'role': user.role.value,
        'redirect_to': _redirect_path(user.role)
    }
    if user.commune_id:
        response['commune_id'] = user.commune_id
    
    return response

@blp.post('/refresh')
@jwt_required(refresh=True)
@blp.response(200, TokenSchema)
@limiter.limit('5 per minute')
def refresh():
    """Refresh access token"""
    user_id = get_current_user_id()
    user = User.query.get(user_id)
    
    if not user or not user.is_active:
        return {'error': 'User not found or inactive'}, 401
    
    additional_claims = {
        'role': user.role.value,
    }
    if user.commune_id:
        additional_claims['commune_id'] = user.commune_id
    
    access_token = create_access_token(
        identity=str(user.id),
        additional_claims=additional_claims
    )
    response = {'access_token': access_token}
    if user.commune_id:
        response['commune_id'] = user.commune_id
    
    return response

@blp.post('/logout')
@jwt_required()
@limiter.limit('5 per minute')
def logout():
    """Logout user - revoke token"""
    token = get_jwt()
    jti = token['jti']
    add_token_to_blacklist(jti, get_current_user_id())
    return {'message': 'Logged out successfully'}, 200

@blp.get('/me')
@jwt_required()
def get_current_user():
    """Get current user info"""
    user_id = get_current_user_id()
    user = User.query.get(user_id)
    
    if not user:
        return {'error': 'User not found'}, 404
    
    response = {
        'id': user.id,
        'username': user.username,
        'email': user.email,
        'role': user.role.value,
        'first_name': user.first_name,
        'last_name': user.last_name,
        'is_active': user.is_active
    }
    if user.commune_id:
        response['commune_id'] = user.commune_id
    
    return response, 200
@blp.patch('/profile')
@jwt_required()
def update_profile():
    """Update user profile information
    
    Allows authenticated users to update their personal information.
    Email uniqueness is enforced.
    
    ---
    security:
      - Bearer: []
    tags:
      - Authentication
    parameters:
      - in: body
        name: body
        schema:
          type: object
          properties:
            first_name:
              type: string
              example: "Ahmed"
              description: User's first name
            last_name:
              type: string
              example: "Ben Salem"
              description: User's last name
            phone:
              type: string
              example: "+216 98 123 456"
              description: Contact phone number
            email:
              type: string
              format: email
              example: "ahmed.bensalem@example.com"
              description: Email address (must be unique)
    responses:
      200:
        description: Profile updated successfully
        content:
          application/json:
            schema:
              type: object
              properties:
                message:
                  type: string
                  example: "Profile updated successfully"
                user_id:
                  type: integer
                  example: 45
      401:
        description: Unauthorized - Invalid or missing JWT token
      404:
        description: User not found
      409:
        description: Email already in use by another user
    """
    user_id = get_current_user_id()
    user = User.query.get(user_id)
    
    if not user:
        return {'error': 'User not found'}, 404
    
    data = request.get_json()
    
    if 'first_name' in data:
        user.first_name = data['first_name']
    if 'last_name' in data:
        user.last_name = data['last_name']
    if 'phone' in data:
        user.phone = data['phone']
    if 'email' in data:
        if User.query.filter(User.email == data['email'], User.id != user_id).first():
            return {'error': ErrorMessages.DUPLICATE_EMAIL}, 409
        user.email = data['email']
    
    db.session.commit()
    
    return {
        'message': 'Profile updated successfully',
        'user_id': user_id
    }, 200

@blp.post('/change-password')
@jwt_required()
def change_password():
    """Change user password
    
    Allows authenticated users to change their password. Requires current password
    for verification. New password must meet complexity requirements.
    
    ---
    security:
      - Bearer: []
    tags:
      - Authentication
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required: [old_password, new_password]
          properties:
            old_password:
              type: string
              example: "OldPass123!"
              description: Current password for verification
            new_password:
              type: string
              example: "NewSecurePass456!"
              description: New password (min 8 chars, must contain uppercase, lowercase, number, special char)
    responses:
      200:
        description: Password changed successfully
        content:
          application/json:
            schema:
              type: object
              properties:
                message:
                  type: string
                  example: "Password changed successfully"
      400:
        description: Missing required fields or new password doesn't meet requirements
        content:
          application/json:
            schema:
              type: object
              properties:
                error:
                  type: string
                  example: "Password must be at least 8 characters and contain uppercase, lowercase, number, and special character"
      401:
        description: Old password is incorrect or JWT token invalid
      404:
        description: User not found
    """
    user_id = get_current_user_id()
    user = User.query.get(user_id)
    
    if not user:
        return {'error': 'User not found'}, 404
    
    data = request.get_json()
    
    if not data.get('old_password') or not data.get('new_password'):
        return {'error': 'old_password and new_password required'}, 400
    
    if not user.check_password(data['old_password']):
        return {'error': 'Old password is incorrect'}, 401
    
    is_valid, msg = Validators.validate_password(data['new_password'])
    if not is_valid:
        return {'error': msg}, 400
    
    user.set_password(data['new_password'])
    db.session.commit()
    
    return {
        'message': 'Password changed successfully'
    }, 200

@blp.post('/upload-document')
@jwt_required()
def upload_document():
    """Deprecated: use /api/declarations/<id>/documents with file upload."""
    return {
        'error': 'Deprecated endpoint',
        'message': 'Use /api/declarations/<id>/documents with multipart upload'
    }, 410

# Two-Factor Authentication endpoints

@blp.post('/2fa/setup')
@jwt_required()
@limiter.limit('10 per minute')
def setup_2fa():
    """Initialize 2FA setup and return QR code for user to scan with authenticator app.
    
    Returns:
        - qr_code_base64: QR code image as base64 string (embed in <img src="data:image/png;base64,...">)
        - secret_key: Raw secret key (for manual entry if camera unavailable)
        - backup_codes: List of 10 backup codes for emergency access
        - uri: Provisioning URI (for debugging)
    """
    from models.two_factor import TwoFactorAuth
    
    user_id = get_current_user_id()
    user = User.query.get(user_id)
    
    if not user:
        return {'error': 'User not found'}, 404
    
    # Check if 2FA already enabled
    existing_2fa = TwoFactorAuth.query.filter_by(user_id=user.id).first()
    if existing_2fa and existing_2fa.is_enabled:
        return {'error': '2FA is already enabled for this account'}, 409
    
    # Create or reset 2FA record
    if not existing_2fa:
        two_fa = TwoFactorAuth(user_id=user.id)
        db.session.add(two_fa)
        db.session.flush()
    else:
        two_fa = existing_2fa
        # Regenerate new secret and backup codes
        two_fa.secret_key = __import__('pyotp').random_base32()
        two_fa.backup_codes = two_fa._generate_backup_codes()
    
    db.session.commit()
    
    return {
        'qr_code_base64': two_fa.get_qr_code_base64(user.email),
        'secret_key': two_fa.secret_key,
        'backup_codes': two_fa.get_backup_codes(),
        'uri': two_fa.get_provisioning_uri(user.email),
        'issuer': 'TUNAX Tax System'
    }, 200


@blp.post('/2fa/verify-and-enable')
@jwt_required()
@limiter.limit('10 per minute')
def verify_and_enable_2fa():
    """Verify TOTP token and enable 2FA for the account.
    
    Required JSON:
        - totp_token: 6-digit code from authenticator app
    """
    from models.two_factor import TwoFactorAuth
    
    user_id = get_current_user_id()
    user = User.query.get(user_id)
    
    if not user:
        return {'error': 'User not found'}, 404
    
    data = request.get_json() or {}
    totp_token = data.get('totp_token', '').strip()
    
    if not totp_token or len(totp_token) != 6 or not totp_token.isdigit():
        return {'error': 'totp_token must be a 6-digit number'}, 400
    
    two_fa = TwoFactorAuth.query.filter_by(user_id=user.id).first()
    
    if not two_fa:
        return {'error': '2FA setup not initiated. Call /2fa/setup first'}, 409
    
    if two_fa.is_enabled:
        return {'error': '2FA is already enabled for this account'}, 409
    
    # Verify the token
    if not two_fa.verify_token(totp_token):
        return {'error': 'Invalid TOTP token. Please try again.'}, 401
    
    # Enable 2FA
    two_fa.is_enabled = True
    db.session.commit()
    
    return {
        'message': '2FA has been successfully enabled',
        'backup_codes': two_fa.get_backup_codes(),
        'warning': 'Save your backup codes in a secure location'
    }, 200


@blp.post('/2fa/disable')
@jwt_required()
@limiter.limit('5 per minute')
def disable_2fa():
    """Disable 2FA for the account. Requires current password for security.
    
    Required JSON:
        - password: Current user password
    """
    from models.two_factor import TwoFactorAuth
    
    user_id = get_current_user_id()
    user = User.query.get(user_id)
    
    if not user:
        return {'error': 'User not found'}, 404
    
    data = request.get_json() or {}
    password = data.get('password', '').strip()
    
    if not password:
        return {'error': 'password required for security confirmation'}, 400
    
    # Verify password
    if not user.check_password(password):
        return {'error': 'Invalid password'}, 401
    
    two_fa = TwoFactorAuth.query.filter_by(user_id=user.id).first()
    
    if not two_fa or not two_fa.is_enabled:
        return {'error': '2FA is not enabled for this account'}, 409
    
    # Disable 2FA
    two_fa.is_enabled = False
    db.session.commit()
    
    return {
        'message': '2FA has been successfully disabled'
    }, 200


@blp.get('/2fa/status')
@jwt_required()
def get_2fa_status():
    """Check if 2FA is enabled for the current user."""
    from models.two_factor import TwoFactorAuth
    
    user_id = get_current_user_id()
    user = User.query.get(user_id)
    
    if not user:
        return {'error': 'User not found'}, 404
    
    two_fa = TwoFactorAuth.query.filter_by(user_id=user.id).first()
    
    return {
        'is_enabled': two_fa.is_enabled if two_fa else False,
        'last_used': two_fa.last_used.isoformat() if two_fa and two_fa.last_used else None,
        'remaining_backup_codes': len(two_fa.get_backup_codes()) if two_fa else 0
    }, 200