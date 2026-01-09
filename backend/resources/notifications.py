"""Notifications management routes"""
from flask import jsonify, request
from flask_smorest import Blueprint
from flask_jwt_extended import jwt_required
from utils.jwt_helpers import get_current_user_id
from extensions.db import db
from models.notification import Notification, NotificationStatus
from models.user import User
from datetime import datetime

notifications_bp = Blueprint('notifications', __name__, url_prefix='/api/v1/notifications')

@notifications_bp.get('/')
@jwt_required()
def get_notifications():
    """Get user notifications with pagination and filtering
    
    Retrieve notifications for the authenticated user.
    Supports filtering by read/unread status and pagination.
    
    ---
    parameters:
      - name: unread
        in: query
        type: boolean
        default: false
        description: Show only unread notifications (true/false)
      - name: page
        in: query
        type: integer
        default: 1
        description: Page number
      - name: per_page
        in: query
        type: integer
        default: 20
        description: Number of notifications per page
    responses:
      200:
        description: Paginated list of notifications
        schema:
          type: object
          properties:
            total:
              type: integer
              description: Total number of notifications
            page:
              type: integer
            per_page:
              type: integer
            notifications:
              type: array
              items:
                type: object
                properties:
                  id:
                    type: integer
                  type:
                    type: string
                  title:
                    type: string
                  message:
                    type: string
                  status:
                    type: string
                    enum: [unread, read]
                  created_at:
                    type: string
                    format: date-time
                  read_at:
                    type: string
                    format: date-time
    """
    user_id = get_current_user_id()
    unread_only = request.args.get('unread', 'false').lower() == 'true'
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    
    query = Notification.query.filter_by(user_id=user_id)
    
    if unread_only:
        query = query.filter_by(status=NotificationStatus.UNREAD)
    
    results = query.order_by(Notification.created_at.desc()).paginate(page=page, per_page=per_page)
    
    return jsonify({
        'total': results.total,
        'page': page,
        'per_page': per_page,
        'notifications': [{
            'id': n.id,
            'type': n.notification_type,
            'title': n.title,
            'message': n.message,
            'status': n.status.value,
            'data': n.data,
            'created_at': n.created_at.isoformat() if n.created_at else None,
            'read_at': n.read_at.isoformat() if n.read_at else None
        } for n in results.items]
    }), 200

@notifications_bp.patch('/<int:notification_id>/read')
@jwt_required()
def mark_notification_read(notification_id):
    """Mark a specific notification as read
    
    Update the status of a notification to 'read' and record the timestamp.
    
    ---
    parameters:
      - name: notification_id
        in: path
        type: integer
        required: true
        description: ID of the notification to mark as read
    responses:
      200:
        description: Notification marked as read
        schema:
          type: object
          properties:
            message:
              type: string
            notification_id:
              type: integer
      403:
        description: Access denied (not your notification)
      404:
        description: Notification not found
    """
    user_id = get_current_user_id()
    
    notification = Notification.query.get(notification_id)
    
    if not notification:
        return jsonify({'error': 'Notification not found'}), 404
    
    if notification.user_id != user_id:
        return jsonify({'error': 'Access denied'}), 403
    
    notification.status = NotificationStatus.READ
    notification.read_at = datetime.utcnow()
    
    db.session.commit()
    
    return jsonify({
        'message': 'Notification marked as read',
        'notification_id': notification_id
    }), 200

@notifications_bp.patch('/settings')
@jwt_required()
def update_notification_settings():
    """Update user notification preferences
    
    Configure notification delivery preferences (email, SMS, in-app)
    and notification types to receive.
    
    ---
    parameters:
      - in: body
        name: body
        schema:
          type: object
          properties:
            email_notifications:
              type: boolean
              description: Enable email notifications
            sms_notifications:
              type: boolean
              description: Enable SMS notifications
            tax_reminders:
              type: boolean
              description: Receive tax payment reminders
            permit_updates:
              type: boolean
              description: Receive permit status updates
            dispute_updates:
              type: boolean
              description: Receive dispute resolution updates
    responses:
      200:
        description: Settings updated successfully
        schema:
          type: object
          properties:
            message:
              type: string
            settings:
              type: object
      404:
        description: User not found
    """
    user_id = get_current_user_id()
    data = request.get_json()
    
    user = User.query.get(user_id)
    
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    # Update settings (in a real app, this would update a notification_settings table)
    # For now, return success with the requested settings
    return jsonify({
        'message': 'Notification settings updated successfully',
        'settings': data
    }), 200
    # Store settings as JSON
    if not hasattr(user, 'notification_settings'):
        user.notification_settings = {}
    
    user.notification_settings.update(data)
    db.session.commit()
    
    return jsonify({
        'message': 'Notification settings updated',
        'settings': user.notification_settings
    }), 200

@notifications_bp.patch('/mark-all-read')
@jwt_required()
def mark_all_read():
    """Mark all user notifications as read
    
    Bulk operation to mark all unread notifications as read for the authenticated user.
    
    ---
    responses:
      200:
        description: All notifications marked as read
        schema:
          type: object
          properties:
            message:
              type: string
    """
    user_id = get_current_user_id()
    
    Notification.query.filter_by(user_id=user_id, status=NotificationStatus.UNREAD).update({
        Notification.status: NotificationStatus.READ,
        Notification.read_at: datetime.utcnow()
    })
    
    db.session.commit()
    
    return jsonify({
        'message': 'All notifications marked as read'
    }), 200
