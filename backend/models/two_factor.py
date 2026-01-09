"""Two-Factor Authentication model"""
from extensions.db import db
from datetime import datetime
import pyotp
import qrcode
from io import BytesIO
import base64

class TwoFactorAuth(db.Model):
    __tablename__ = 'two_factor_auth'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, unique=True)
    secret_key = db.Column(db.String(32), nullable=False)
    is_enabled = db.Column(db.Boolean, default=False)
    backup_codes = db.Column(db.Text)  # JSON array of backup codes
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_used = db.Column(db.DateTime)
    
    # Relationship
    user = db.relationship('User', backref=db.backref('two_factor', uselist=False))
    
    def __init__(self, user_id):
        self.user_id = user_id
        self.secret_key = pyotp.random_base32()
        self.is_enabled = False
        self.backup_codes = self._generate_backup_codes()
    
    def _generate_backup_codes(self):
        """Generate 10 backup codes"""
        import json
        import secrets
        codes = [secrets.token_hex(4).upper() for _ in range(10)]
        return json.dumps(codes)
    
    def get_backup_codes(self):
        """Get backup codes as list"""
        import json
        return json.loads(self.backup_codes) if self.backup_codes else []
    
    def use_backup_code(self, code):
        """Use a backup code (remove it from list)"""
        import json
        codes = self.get_backup_codes()
        if code.upper() in codes:
            codes.remove(code.upper())
            self.backup_codes = json.dumps(codes)
            return True
        return False
    
    def get_provisioning_uri(self, user_email):
        """Get TOTP provisioning URI for QR code"""
        totp = pyotp.TOTP(self.secret_key)
        return totp.provisioning_uri(
            name=user_email,
            issuer_name='TUNAX Tax System'
        )
    
    def get_qr_code_base64(self, user_email):
        """Generate QR code as base64 string"""
        uri = self.get_provisioning_uri(user_email)
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(uri)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)
        return base64.b64encode(buffer.getvalue()).decode()
    
    def verify_token(self, token):
        """Verify TOTP token"""
        totp = pyotp.TOTP(self.secret_key)
        return totp.verify(token, valid_window=1)  # Allow 30s window
    
    def __repr__(self):
        return f'<TwoFactorAuth user_id={self.user_id} enabled={self.is_enabled}>'
