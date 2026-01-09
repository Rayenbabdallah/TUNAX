"""Two-Factor Authentication endpoints"""
from flask import jsonify, request
from flask_smorest import Blueprint
from flask_jwt_extended import jwt_required, get_jwt_identity
from extensions.db import db
from models.user import User
from models.two_factor import TwoFactorAuth
from utils.validators import ErrorMessages
from marshmallow import Schema, fields

blp = Blueprint('two_factor', 'two_factor', url_prefix='/api/v1/two-factor')


class TwoFactorEnableSchema(Schema):
    """Schema for enabling 2FA"""
    token = fields.Str(required=True)


class TwoFactorVerifySchema(Schema):
    """Schema for verifying 2FA"""
    token = fields.Str(required=True)


class BackupCodesSchema(Schema):
    """Schema for backup codes"""
    token = fields.Str(required=True)


@blp.get('/setup')
@blp.post('/setup')
@blp.response(200)
@jwt_required()
def setup_2fa():
    """Initialize 2FA setup - generate secret and QR code"""
    user_id = int(get_jwt_identity())
    user = User.query.get(user_id)
    
    if not user:
        return jsonify({'error': ErrorMessages.NOT_FOUND}), 404
    
    # Check if 2FA already exists
    two_fa = TwoFactorAuth.query.filter_by(user_id=user_id).first()
    
    if two_fa:
        if two_fa.is_enabled:
            return jsonify({'error': '2FA is already enabled'}), 400
        # Regenerate secret if not enabled yet
        db.session.delete(two_fa)
        db.session.commit()
    
    # Create new 2FA setup
    two_fa = TwoFactorAuth(user_id=user_id)
    db.session.add(two_fa)
    db.session.commit()
    
    return jsonify({
        'message': '2FA setup initiated',
        'secret_key': two_fa.secret_key,
        'qr_code': f'data:image/png;base64,{two_fa.get_qr_code_base64(user.email)}',
        'backup_codes': two_fa.get_backup_codes(),
        'manual_entry_key': two_fa.secret_key
    }), 200

@blp.post('/enable')
@blp.arguments(TwoFactorEnableSchema, location="json")
@blp.response(200)
@jwt_required()
def enable_2fa(data):
    """Enable 2FA after verifying initial token"""
    user_id = int(get_jwt_identity())
    
    if not data.get('token'):
        return jsonify({'error': 'Verification token required'}), 400
    
    two_fa = TwoFactorAuth.query.filter_by(user_id=user_id).first()
    
    if not two_fa:
        return jsonify({'error': '2FA not set up. Call /api/2fa/setup first'}), 400
    
    if two_fa.is_enabled:
        return jsonify({'error': '2FA is already enabled'}), 400
    
    # Verify token
    if not two_fa.verify_token(data['token']):
        return jsonify({'error': 'Invalid verification token'}), 400
    
    # Enable 2FA
    two_fa.is_enabled = True
    db.session.commit()
    
    return jsonify({
        'message': '2FA enabled successfully',
        'backup_codes': two_fa.get_backup_codes()
    }), 200

@blp.post('/disable')
@blp.arguments(TwoFactorEnableSchema, location="json")
@blp.response(200)
@jwt_required()
def disable_2fa(data):
    """Disable 2FA after verifying token"""
    user_id = int(get_jwt_identity())
    
    if not data.get('token') and not data.get('backup_code'):
        return jsonify({'error': 'Verification token or backup code required'}), 400
    
    two_fa = TwoFactorAuth.query.filter_by(user_id=user_id).first()
    
    if not two_fa or not two_fa.is_enabled:
        return jsonify({'error': '2FA is not enabled'}), 400
    
    # Verify token or backup code
    if data.get('token'):
        if not two_fa.verify_token(data['token']):
            return jsonify({'error': 'Invalid verification token'}), 400
    elif data.get('backup_code'):
        if not two_fa.use_backup_code(data['backup_code']):
            return jsonify({'error': 'Invalid backup code'}), 400
    
    # Disable and delete 2FA
    db.session.delete(two_fa)
    db.session.commit()
    
    return jsonify({'message': '2FA disabled successfully'}), 200

@blp.get('/status')
@blp.response(200)
@jwt_required()
def get_2fa_status():
    """Get current 2FA status"""
    user_id = int(get_jwt_identity())
    two_fa = TwoFactorAuth.query.filter_by(user_id=user_id).first()
    
    return jsonify({
        'enabled': two_fa.is_enabled if two_fa else False,
        'has_backup_codes': len(two_fa.get_backup_codes()) > 0 if two_fa else False,
        'backup_codes_count': len(two_fa.get_backup_codes()) if two_fa else 0
    }), 200

@blp.post('/regenerate-backup-codes')
@blp.arguments(TwoFactorEnableSchema, location="json")
@blp.response(200)
@jwt_required()
def regenerate_backup_codes(data):
    
    if not data.get('token'):
        return jsonify({'error': 'Verification token required'}), 400
    
    two_fa = TwoFactorAuth.query.filter_by(user_id=user_id).first()
    
    if not two_fa or not two_fa.is_enabled:
        return jsonify({'error': '2FA is not enabled'}), 400
    
    # Verify token
    if not two_fa.verify_token(data['token']):
        return jsonify({'error': 'Invalid verification token'}), 400
    
    # Regenerate backup codes
    two_fa.backup_codes = two_fa._generate_backup_codes()
    db.session.commit()
    
    return jsonify({
        'message': 'Backup codes regenerated',
        'backup_codes': two_fa.get_backup_codes()
    }), 200
