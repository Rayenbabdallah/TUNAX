"""Service reclamation routes"""
from flask import jsonify, request
from flask_smorest import Blueprint
from flask_jwt_extended import jwt_required
from utils.jwt_helpers import get_current_user_id
from extensions.db import db
from models.user import User, UserRole
from models.reclamation import Reclamation, ReclamationType, ReclamationStatus
from schemas import ReclamationSchema
from utils.role_required import citizen_or_business_required, agent_required
from utils.validators import ErrorMessages
from marshmallow import ValidationError
from datetime import datetime

blp = Blueprint('reclamations', 'reclamations', url_prefix='/api/v1/reclamations')

@blp.post('/')
@jwt_required()
@citizen_or_business_required
def submit_reclamation():
    """Submit a service reclamation/complaint
    
    Create a new reclamation for municipal services such as tax calculation disputes,
    infrastructure issues, service quality complaints, or administrative requests.
    
    ---
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - reclamation_type
            - street_address
            - city
            - description
          properties:
            reclamation_type:
              type: string
              enum: [tax_calculation, infrastructure, service_quality, administrative]
              description: Type of reclamation
            street_address:
              type: string
              description: Street address where issue occurred
            city:
              type: string
              description: City/municipality
            description:
              type: string
              description: Detailed description of the issue
            priority:
              type: string
              enum: [low, medium, high, urgent]
              default: medium
              description: Priority level
    responses:
      201:
        description: Reclamation submitted successfully
        schema:
          type: object
          properties:
            message:
              type: string
            reclamation_id:
              type: integer
            status:
              type: string
              description: Initial status (submitted)
      400:
        description: Invalid input data
    """
    user_id = get_current_user_id()
    
    try:
        schema = ReclamationSchema()
        data = schema.load(request.get_json())
    except ValidationError as err:
        return jsonify({'errors': err.messages}), 400
    
    reclamation = Reclamation(
        user_id=user_id,
        reclamation_type=data['reclamation_type'],
        street_address=data['street_address'],
        city=data['city'],
        description=data['description'],
        priority=data.get('priority', 'medium'),
        status=ReclamationStatus.SUBMITTED,
        created_at=datetime.utcnow()
    )
    
    db.session.add(reclamation)
    db.session.commit()
    
    return jsonify({
        'message': 'Reclamation submitted',
        'reclamation_id': reclamation.id,
        'status': reclamation.status.value
    }), 201

@blp.get('/my-reclamations')
@jwt_required()
@citizen_or_business_required
def get_my_reclamations():
    """Get all reclamations submitted by the current user
    
    Retrieve a list of all reclamations/complaints submitted by the authenticated citizen or business.
    
    ---
    responses:
      200:
        description: List of user's reclamations
        schema:
          type: object
          properties:
            total:
              type: integer
              description: Total number of reclamations
            reclamations:
              type: array
              items:
                type: object
                properties:
                  id:
                    type: integer
                  type:
                    type: string
                    description: Reclamation type
                  street_address:
                    type: string
                  city:
                    type: string
                  status:
                    type: string
                    enum: [submitted, in_progress, resolved, rejected]
                  priority:
                    type: string
                  created_at:
                    type: string
                    format: date-time
                  resolved_date:
                    type: string
                    format: date-time
                    description: Date when reclamation was resolved (null if pending)
    """
    user_id = get_current_user_id()
    
    reclamations = Reclamation.query.filter_by(user_id=user_id).all()
    
    return jsonify({
        'total': len(reclamations),
        'reclamations': [{
            'id': r.id,
            'type': r.reclamation_type.value,
            'street_address': r.street_address,
            'city': r.city,
            'status': r.status.value,
            'priority': r.priority,
            'created_at': r.created_at.isoformat() if r.created_at else None,
            'resolved_date': r.resolved_date.isoformat() if r.resolved_date else None
        } for r in reclamations]
    }), 200

@blp.get('/<int:reclamation_id>')
@jwt_required()
def get_reclamation(reclamation_id):
    """Get reclamation details
    
    Retrieve full details of a specific reclamation.
    Citizens can only view their own reclamations.
    Municipal staff can view all reclamations in their municipality.
    
    ---
    parameters:
      - name: reclamation_id
        in: path
        type: integer
        required: true
        description: ID of the reclamation
    responses:
      200:
        description: Reclamation details
        schema:
          type: object
          properties:
            id:
              type: integer
            user_id:
              type: integer
            type:
              type: string
            street_address:
              type: string
            city:
              type: string
            description:
              type: string
            status:
              type: string
            priority:
              type: string
            assigned_to:
              type: integer
              description: Agent ID (if assigned)
            resolution:
              type: string
              description: Resolution notes (if resolved)
            created_at:
              type: string
              format: date-time
            resolved_date:
              type: string
              format: date-time
      403:
        description: Access denied
      404:
        description: Reclamation not found
    """
    user_id = get_current_user_id()
    user = User.query.get(user_id)
    
    reclamation = Reclamation.query.get(reclamation_id)
    
    if not reclamation:
        return jsonify({'error': ErrorMessages.NOT_FOUND}), 404
    
    # Check access
    if user.role not in [UserRole.MUNICIPAL_ADMIN, UserRole.MUNICIPAL_AGENT] and reclamation.user_id != user_id:
        return jsonify({'error': ErrorMessages.ACCESS_DENIED}), 403
    
    return jsonify({
        'id': reclamation.id,
        'user_id': reclamation.user_id,
        'type': reclamation.reclamation_type.value,
        'street_address': reclamation.street_address,
        'city': reclamation.city,
        'description': reclamation.description,
        'status': reclamation.status.value,
        'priority': reclamation.priority,
        'assigned_to': reclamation.assigned_to,
        'resolution': reclamation.resolution,
        'created_at': reclamation.created_at.isoformat() if reclamation.created_at else None,
        'resolved_date': reclamation.resolved_date.isoformat() if reclamation.resolved_date else None
    }), 200

@blp.get('/all')
@jwt_required()
@agent_required
def get_all_reclamations():
    """Get all reclamations in municipality (for agents)
    
    Retrieve all service reclamations for the municipal agent's assigned municipality.
    Optional status filter can be applied to show only pending, in-progress, or resolved cases.
    
    ---
    parameters:
      - name: status
        in: query
        type: string
        enum: [submitted, in_progress, resolved, rejected]
        description: Filter by reclamation status (optional)
    responses:
      200:
        description: List of reclamations
        schema:
          type: object
          properties:
            total:
              type: integer
            reclamations:
              type: array
              items:
                type: object
                properties:
                  id:
                    type: integer
                  user_id:
                    type: integer
                  type:
                    type: string
                  street_address:
                    type: string
                  city:
                    type: string
                  status:
                    type: string
                  priority:
                    type: string
                  assigned_to:
                    type: integer
                  created_at:
                    type: string
                    format: date-time
    """
    status_filter = request.args.get('status')
    
    query = Reclamation.query
    
    if status_filter:
        query = query.filter_by(status=ReclamationStatus[status_filter.upper()])
    
    reclamations = query.all()
    
    return jsonify({
        'total': len(reclamations),
        'reclamations': [{
            'id': r.id,
            'user_id': r.user_id,
            'type': r.reclamation_type.value,
            'street_address': r.street_address,
            'status': r.status.value,
            'priority': r.priority,
            'assigned_to': r.assigned_to
        } for r in reclamations]
    }), 200

@blp.patch('/<int:reclamation_id>/assign')
@jwt_required()
@agent_required
def assign_reclamation(reclamation_id):
    """Assign reclamation to self"""
    user_id = get_current_user_id()
    
    reclamation = Reclamation.query.get(reclamation_id)
    
    if not reclamation:
        return jsonify({'error': ErrorMessages.NOT_FOUND}), 404
    
    reclamation.assigned_to = user_id
    reclamation.status = ReclamationStatus.ASSIGNED
    
    db.session.commit()
    
    return jsonify({
        'message': 'Reclamation assigned',
        'reclamation_id': reclamation_id
    }), 200

@blp.patch('/<int:reclamation_id>/progress')
@jwt_required()
@agent_required
def update_reclamation_progress(reclamation_id):
    """Update reclamation progress"""
    user_id = get_current_user_id()
    
    reclamation = Reclamation.query.get(reclamation_id)
    
    if not reclamation:
        return jsonify({'error': ErrorMessages.NOT_FOUND}), 404
    
    if reclamation.assigned_to != user_id:
        return jsonify({'error': ErrorMessages.ACCESS_DENIED}), 403
    
    data = request.get_json()
    
    if data.get('status'):
        reclamation.status = ReclamationStatus[data['status'].upper()]
    
    if data.get('resolution'):
        reclamation.resolution = data['resolution']
        reclamation.resolved_date = datetime.utcnow()
        reclamation.status = ReclamationStatus.RESOLVED
    
    db.session.commit()
    
    return jsonify({
        'message': 'Reclamation updated',
        'reclamation_id': reclamation_id,
        'status': reclamation.status.value
    }), 200
