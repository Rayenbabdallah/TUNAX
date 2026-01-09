"""Utility helpers for JWT handling."""
from flask_jwt_extended import get_jwt_identity as _get_jwt_identity


def get_current_user_id():
    """Return the authenticated user id as an int when possible."""
    identity = _get_jwt_identity()
    if identity is None:
        return None
    try:
        return int(identity)
    except (TypeError, ValueError):
        return identity
