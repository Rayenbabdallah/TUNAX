"""JWT extension with persistent token blacklist"""
from flask_jwt_extended import JWTManager
from datetime import datetime
from extensions.db import db

jwt = JWTManager()


class TokenBlacklist(db.Model):
    __tablename__ = "token_blacklist"
    id = db.Column(db.Integer, primary_key=True)
    jti = db.Column(db.String(128), unique=True, nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)


def add_token_to_blacklist(jti: str, user_id: int | None = None) -> None:
    """Persist a JWT jti to the blacklist table."""
    if not jti:
        return
    if not TokenBlacklist.query.filter_by(jti=jti).first():
        db.session.add(TokenBlacklist(jti=jti))
        db.session.commit()


def is_token_blacklisted(jti: str) -> bool:
    """Check if a JWT jti exists in the blacklist table."""
    if not jti:
        return False
    return db.session.query(TokenBlacklist.id).filter_by(jti=jti).first() is not None
