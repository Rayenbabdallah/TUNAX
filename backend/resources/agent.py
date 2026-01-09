"""Municipal Agent routes"""
from flask import jsonify, request
from flask_smorest import Blueprint
from flask_jwt_extended import jwt_required
from utils.jwt_helpers import get_current_user_id
from extensions.db import db
from models.property import Property, PropertyStatus
from models.land import Land, LandStatus
from models.reclamation import Reclamation, ReclamationStatus
from utils.role_required import agent_required
from utils.geo import GeoLocator
from utils.validators import Validators, ErrorMessages
from datetime import datetime

blp = Blueprint('agent', 'agent', url_prefix='/api/v1/agent')

@blp.post('/verify/address')
@jwt_required()
@agent_required
def verify_address():
    """Verify address using Nominatim geocoding service
    
    Validates an address using OpenStreetMap Nominatim API and returns GPS coordinates.
    Agents can manually override coordinates if automatic geocoding fails.
    
    ---
    security:
      - Bearer: []
    tags:
      - Agent
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required: [street, city]
          properties:
            street:
              type: string
              example: "15 Avenue Habib Bourguiba"
              description: Street address to verify
            city:
              type: string
              example: "Tunis"
              description: City name in Tunisia
            override_lat:
              type: number
              format: float
              example: 36.8065
              description: Manual latitude override (optional)
            override_lon:
              type: number
              format: float
              example: 10.1815
              description: Manual longitude override (optional)
    responses:
      200:
        description: Address verified successfully
        content:
          application/json:
            schema:
              type: object
              properties:
                found:
                  type: boolean
                  example: true
                latitude:
                  type: number
                  format: float
                  example: 36.8065
                longitude:
                  type: number
                  format: float
                  example: 10.1815
                address_info:
                  type: object
                  example: {"country": "Tunisia", "city": "Tunis"}
                override:
                  type: boolean
                  example: false
      400:
        description: Missing required fields (street and city)
      404:
        description: Address not found - returns suggestions for nearby streets
        content:
          application/json:
            schema:
              type: object
              properties:
                found:
                  type: boolean
                  example: false
                error:
                  type: string
                  example: "Street not found in external API"
                suggestion:
                  type: string
                  example: "Try the nearest known street or provide GPS coordinates"
                suggestions:
                  type: array
                  items:
                    type: string
                  example: ["Avenue Habib Bourguiba", "Rue de la Liberté"]
    """
    data = request.get_json()
    
    if not data.get('street') or not data.get('city'):
        return jsonify({'error': 'Street and city required'}), 400
    
    # Manual override by inspector/agent if provided
    if data.get('override_lat') is not None and data.get('override_lon') is not None:
        address_info = GeoLocator.reverse_geocode(data['override_lat'], data['override_lon'])
        return jsonify({
            'found': True,
            'latitude': data['override_lat'],
            'longitude': data['override_lon'],
            'address_info': address_info,
            'override': True
        }), 200

    lat, lon = GeoLocator.geocode_address(data['street'], data['city'])
    
    if lat is None:
        nearby = GeoLocator.get_nearby_streets(data['city'], data['street'])
        return jsonify({
            'found': False,
            'error': "Street not found in external API",
            'suggestion': "Try the nearest known street or provide GPS coordinates",
            'suggestions': nearby[:5]
        }), 404
    
    address_info = GeoLocator.reverse_geocode(lat, lon)
    
    return jsonify({
        'found': True,
        'latitude': lat,
        'longitude': lon,
        'address_info': address_info
    }), 200

@blp.post('/verify/property/<int:property_id>')
@jwt_required()
@agent_required
def verify_property(property_id):
    """Verify property declaration after inspection
    
    Agents/inspectors can verify property details and update information based on
    on-site inspection or satellite imagery verification.
    
    ---
    security:
      - Bearer: []
    tags:
      - Agent
    parameters:
      - in: path
        name: property_id
        required: true
        schema:
          type: integer
          example: 123
        description: ID of the property to verify
      - in: body
        name: body
        schema:
          type: object
          properties:
            surface_couverte:
              type: number
              format: float
              example: 152.5
              description: Verified covered surface area in m²
            affectation:
              type: string
              enum: [residential, commercial, industrial, mixed]
              example: "residential"
              description: Verified property usage type
            notes:
              type: string
              example: "Property verified via satellite imagery. Surface matches declaration."
              description: Verification notes from agent
    responses:
      200:
        description: Property verified successfully
        content:
          application/json:
            schema:
              type: object
              properties:
                message:
                  type: string
                  example: "Property verified"
                property_id:
                  type: integer
                  example: 123
                status:
                  type: string
                  example: "verified"
      401:
        description: Unauthorized - Invalid or missing JWT token
      403:
        description: Forbidden - User is not an agent/inspector
      404:
        description: Property not found
    """
    prop = Property.query.get(property_id)
    
    if not prop:
        return jsonify({'error': ErrorMessages.NOT_FOUND}), 404
    
    data = request.get_json()
    
    # Validate and update property
    if data.get('surface_couverte'):
        prop.surface_couverte = data['surface_couverte']
    
    if data.get('affectation'):
        prop.affectation = data['affectation']
    
    if data.get('notes'):
        prop.satellite_notes = data['notes']
    
    # Mark as verified
    prop.status = PropertyStatus.VERIFIED
    prop.satellite_verified = True
    prop.satellite_verification_date = datetime.utcnow()
    
    db.session.commit()
    
    return jsonify({
        'message': 'Property verified',
        'property_id': property_id,
        'status': prop.status.value
    }), 200

@blp.post('/verify/land/<int:land_id>')
@jwt_required()
@agent_required
def verify_land(land_id):
    """Verify land declaration"""
    land = Land.query.get(land_id)
    
    if not land:
        return jsonify({'error': ErrorMessages.NOT_FOUND}), 404
    
    data = request.get_json()
    
    # Validate and update land
    if data.get('surface'):
        land.surface = data['surface']
    
    if data.get('land_type'):
        land.land_type = data['land_type']
    
    if data.get('notes'):
        land.satellite_notes = data['notes']
    
    # Mark as verified
    land.status = LandStatus.VERIFIED
    land.satellite_verified = True
    land.satellite_verification_date = datetime.utcnow()
    
    db.session.commit()
    
    return jsonify({
        'message': 'Land verified',
        'land_id': land_id,
        'status': land.status.value
    }), 200

@blp.get('/reclamations')
@jwt_required()
@agent_required
def get_assigned_reclamations():
    """Get reclamations assigned to agent"""
    user_id = get_current_user_id()
    
    reclamations = Reclamation.query.filter_by(assigned_to=user_id).all()
    
    return jsonify({
        'total': len(reclamations),
        'reclamations': [{
            'id': r.id,
            'type': r.reclamation_type.value,
            'street_address': r.street_address,
            'city': r.city,
            'status': r.status.value,
            'priority': r.priority,
            'created_at': r.created_at.isoformat() if r.created_at else None
        } for r in reclamations]
    }), 200

@blp.patch('/reclamations/<int:reclamation_id>/assign')
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
        'reclamation_id': reclamation_id,
        'status': reclamation.status.value
    }), 200

@blp.patch('/reclamations/<int:reclamation_id>/update')
@jwt_required()
@agent_required
def update_reclamation(reclamation_id):
    """Update reclamation status"""
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

# Route aliases for backward compatibility with test collection
@blp.post('/verify-address')
@jwt_required()
@agent_required
def verify_address_alias():
    """Alias for verify/address endpoint"""
    return verify_address()

@blp.patch('/property/<int:property_id>/verify')
@jwt_required()
@agent_required
def verify_property_alias(property_id):
    """Alias for verify/property endpoint"""
    return verify_property(property_id)

@blp.patch('/land/<int:land_id>/verify')
@jwt_required()
@agent_required
def verify_land_alias(land_id):
    """Alias for verify/land endpoint"""
    return verify_land(land_id)

@blp.patch('/reclamation/<int:reclamation_id>/assign')
@jwt_required()
@agent_required
def assign_reclamation_alias(reclamation_id):
    """Alias for reclamations/assign endpoint"""
    return assign_reclamation(reclamation_id)

@blp.patch('/reclamation/<int:reclamation_id>/update')
@jwt_required()
@agent_required
def update_reclamation_alias(reclamation_id):
    """Alias for reclamations/update endpoint"""
    return update_reclamation(reclamation_id)
