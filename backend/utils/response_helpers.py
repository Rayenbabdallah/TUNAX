"""Common response helpers to reduce code duplication across resources"""
from flask import jsonify
from models.user import User
from utils.jwt_helpers import get_current_user_id


def error_response(message, status_code=400):
    """Standard error response format"""
    return jsonify({'error': message}), status_code


def success_response(message, data=None, status_code=200):
    """Standard success response format"""
    response = {'message': message}
    if data:
        response.update(data)
    return jsonify(response), status_code


def not_found_response(resource_type="Resource"):
    """Standard 404 response"""
    return jsonify({'error': f'{resource_type} not found'}), 404


def access_denied_response(message="You don't have permission to access this resource"):
    """Standard 403 response"""
    return jsonify({'error': message}), 403


def get_current_user():
    """Get current user object from JWT token"""
    user_id = get_current_user_id()
    return User.query.get(user_id)


def verify_ownership(resource, user_id, owner_field='owner_id'):
    """
    Verify that a user owns a resource
    
    Args:
        resource: Database model instance
        user_id: Current user ID
        owner_field: Name of the owner field (default: 'owner_id')
    
    Returns:
        tuple: (is_owner: bool, error_response or None)
    """
    if not resource:
        return False, not_found_response()
    
    resource_owner_id = getattr(resource, owner_field, None)
    if resource_owner_id != user_id:
        return False, access_denied_response()
    
    return True, None


def paginate_query(query, page=1, per_page=50):
    """
    Paginate a SQLAlchemy query
    
    Args:
        query: SQLAlchemy query object
        page: Page number (default: 1)
        per_page: Items per page (default: 50)
    
    Returns:
        dict: Pagination metadata and items
    """
    pagination = query.paginate(
        page=page,
        per_page=per_page,
        error_out=False
    )
    
    return {
        'items': pagination.items,
        'total': pagination.total,
        'page': page,
        'per_page': per_page,
        'pages': pagination.pages,
        'has_next': pagination.has_next,
        'has_prev': pagination.has_prev
    }


def serialize_model(model_instance, exclude_fields=None):
    """
    Serialize a model instance to dict
    
    Args:
        model_instance: SQLAlchemy model instance
        exclude_fields: List of field names to exclude
    
    Returns:
        dict: Serialized model data
    """
    if hasattr(model_instance, 'to_dict'):
        return model_instance.to_dict()
    
    exclude_fields = exclude_fields or []
    result = {}
    
    for column in model_instance.__table__.columns:
        if column.name not in exclude_fields:
            value = getattr(model_instance, column.name)
            # Handle datetime serialization
            if hasattr(value, 'isoformat'):
                value = value.isoformat()
            # Handle enum serialization
            elif hasattr(value, 'value'):
                value = value.value
            result[column.name] = value
    
    return result
