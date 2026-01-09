"""Inspector routes"""
from flask import jsonify, request
from flask_smorest import Blueprint
from flask_jwt_extended import jwt_required
from utils.jwt_helpers import get_current_user_id
from extensions.db import db
from models.property import Property, PropertyStatus
from models.land import Land, LandStatus
from models.inspection import Inspection, InspectionStatus
from models.user import User
from schemas import InspectionReportSchema
from utils.role_required import inspector_required
from utils.geo import SatelliteImagery
from utils.validators import ErrorMessages
from marshmallow import ValidationError, Schema, fields
from datetime import datetime

blp = Blueprint('inspector', 'inspector', url_prefix='/api/v1/inspector')


class InspectionReportInputSchema(Schema):
    """Schema for inspection report input"""
    findings = fields.Str(required=True)
    status = fields.Str(required=True)
    risk_level = fields.Str(allow_none=True)

@blp.get('/properties/to-inspect')
@blp.response(200)
@jwt_required()
@inspector_required
def get_properties_to_inspect():
    """Get properties awaiting satellite verification inspection
    
    Retrieve all properties in the inspector's municipality that have been declared but not yet
    verified through satellite imagery inspection. Inspectors can only see properties within their
    assigned municipality.
    
    ---
    responses:
      200:
        description: List of properties awaiting inspection
        schema:
          type: object
          properties:
            count:
              type: integer
              description: Number of properties awaiting inspection
            properties:
              type: array
              items:
                type: object
                properties:
                  id:
                    type: integer
                  owner_id:
                    type: integer
                  street_address:
                    type: string
                  city:
                    type: string
                  surface_couverte:
                    type: number
                    description: Declared covered surface in m²
                  affectation:
                    type: string
                    description: Property usage type
                  latitude:
                    type: number
                  longitude:
                    type: number
                  status:
                    type: string
                    description: Property status
    """
    user_id = get_current_user_id()
    user = User.query.get(user_id)
    
    # Get properties that haven't been verified AND are in the inspector's municipality
    properties = Property.query.filter_by(
        satellite_verified=False,
        commune_id=user.commune_id
    ).all()
    
    return jsonify({
        'count': len(properties),
        'properties': [{
            'id': p.id,
            'owner_id': p.owner_id,
            'street_address': p.street_address,
            'city': p.city,
            'surface_couverte': p.surface_couverte,
            'affectation': p.affectation.value if hasattr(p.affectation, 'value') else p.affectation,
            'latitude': p.latitude,
            'longitude': p.longitude,
            'status': p.status.value
        } for p in properties]
    }), 200

@blp.get('/lands/to-inspect')
@blp.response(200)
@jwt_required()
@inspector_required
def get_lands_to_inspect():
    """Get land parcels awaiting satellite verification inspection
    
    Retrieve all land parcels in the inspector's municipality that have been declared but not yet
    verified through satellite imagery inspection. Inspectors can only see lands within their
    assigned municipality.
    
    ---
    responses:
      200:
        description: List of land parcels awaiting inspection
        schema:
          type: object
          properties:
            count:
              type: integer
              description: Number of lands awaiting inspection
            lands:
              type: array
              items:
                type: object
                properties:
                  id:
                    type: integer
                  owner_id:
                    type: integer
                  street_address:
                    type: string
                  city:
                    type: string
                  surface:
                    type: number
                    description: Declared surface area in m²
                  land_type:
                    type: string
                    description: Land usage type
                  latitude:
                    type: number
                  longitude:
                    type: number
                  status:
                    type: string
                    description: Land status
    """
    user_id = get_current_user_id()
    user = User.query.get(user_id)
    
    # Get lands that haven't been verified AND are in the inspector's municipality
    lands = Land.query.filter_by(
        satellite_verified=False,
        commune_id=user.commune_id
    ).all()
    
    return jsonify({
        'count': len(lands),
        'lands': [{
            'id': l.id,
            'owner_id': l.owner_id,
            'street_address': l.street_address,
            'city': l.city,
            'surface': l.surface,
            'land_type': l.land_type.value if hasattr(l.land_type, 'value') else l.land_type,
            'latitude': l.latitude,
            'longitude': l.longitude,
            'status': l.status.value
        } for l in lands]
    }), 200

@blp.post('/report')
@blp.arguments(InspectionReportInputSchema, location="json")
@blp.response(201)
@jwt_required()
@inspector_required
def submit_inspection_report(data):
    """Submit inspection report"""
    user_id = get_current_user_id()
    
    try:
        schema = InspectionReportSchema()
        data = schema.load(request.get_json())
    except ValidationError as err:
        return jsonify({'errors': err.messages}), 400
    
    # Create inspection record
    inspection = Inspection(
        inspector_id=user_id,
        property_id=data.get('property_id'),
        land_id=data.get('land_id'),
        status=InspectionStatus.COMPLETED,
        notes=data.get('notes'),
        satellite_verified=data.get('satellite_verified', False),
        discrepancies_found=data.get('discrepancies_found', False),
        evidence_urls=data.get('evidence_urls'),
        recommendation=data.get('recommendation'),
        date=datetime.utcnow()
    )
    
    db.session.add(inspection)
    
    # Update property or land
    if data.get('property_id'):
        prop = Property.query.get(data['property_id'])
        if prop:
            prop.satellite_verified = True
            prop.satellite_verification_date = datetime.utcnow()
            prop.satellite_notes = data.get('notes')
            if data.get('discrepancies_found'):
                prop.status = PropertyStatus.DISPUTED
    
    if data.get('land_id'):
        land = Land.query.get(data['land_id'])
        if land:
            land.satellite_verified = True
            land.satellite_verification_date = datetime.utcnow()
            land.satellite_notes = data.get('notes')
            if data.get('discrepancies_found'):
                land.status = LandStatus.DISPUTED
    
    db.session.commit()
    
    return jsonify({
        'message': 'Inspection report submitted',
        'inspection_id': inspection.id,
        'status': inspection.status.value
    }), 201

@blp.get('/report/<int:inspection_id>')
@blp.response(200)
@jwt_required()
@inspector_required
def get_inspection_report(inspection_id):
    """Get inspection report"""
    inspection = Inspection.query.get(inspection_id)
    
    if not inspection:
        return jsonify({'error': ErrorMessages.NOT_FOUND}), 404
    
    return jsonify({
        'id': inspection.id,
        'inspector_id': inspection.inspector_id,
        'property_id': inspection.property_id,
        'land_id': inspection.land_id,
        'status': inspection.status.value,
        'date': inspection.date.isoformat() if inspection.date else None,
        'notes': inspection.notes,
        'satellite_verified': inspection.satellite_verified,
        'discrepancies_found': inspection.discrepancies_found,
        'evidence_urls': inspection.evidence_urls,
        'recommendation': inspection.recommendation
    }), 200

@blp.get('/property/<int:property_id>/satellite-imagery')
@blp.response(200)
@jwt_required()
@inspector_required
def get_property_satellite_imagery(property_id):
    """Get satellite imagery info for property"""
    prop = Property.query.get(property_id)
    
    if not prop:
        return jsonify({'error': ErrorMessages.NOT_FOUND}), 404
    
    if not prop.latitude or not prop.longitude:
        return jsonify({'error': 'Property coordinates not available'}), 400
    
    imagery_info = SatelliteImagery.get_satellite_imagery_info(
        prop.latitude,
        prop.longitude
    )
    
    return jsonify(imagery_info), 200

@blp.get('/land/<int:land_id>/satellite-imagery')
@blp.response(200)
@jwt_required()
@inspector_required
def get_land_satellite_imagery(land_id):
    """Get satellite imagery info for land"""
    land = Land.query.get(land_id)
    
    if not land:
        return jsonify({'error': ErrorMessages.NOT_FOUND}), 404
    
    if not land.latitude or not land.longitude:
        return jsonify({'error': 'Land coordinates not available'}), 400
    
    imagery_info = SatelliteImagery.get_satellite_imagery_info(
        land.latitude,
        land.longitude
    )
    
    return jsonify(imagery_info), 200

@blp.get('/my-reports')
@blp.response(200)
@jwt_required()
@inspector_required
def get_my_reports():
    """Get my inspection reports"""
    user_id = get_current_user_id()
    
    inspections = Inspection.query.filter_by(inspector_id=user_id).all()
    
    return jsonify({
        'total': len(inspections),
        'inspections': [{
            'id': i.id,
            'property_id': i.property_id,
            'land_id': i.land_id,
            'status': i.status.value,
            'date': i.date.isoformat() if i.date else None,
            'discrepancies_found': i.discrepancies_found
        } for i in inspections]
    }), 200
