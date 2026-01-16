"""Dispute and Contentieux management routes"""
from flask import jsonify, request
from flask_smorest import Blueprint
from flask_jwt_extended import jwt_required
from utils.jwt_helpers import get_current_user_id
from extensions.db import db
from models.user import User, UserRole
from models.dispute import Dispute, DisputeStatus, DisputeType
from schemas import DisputeSchema, DisputeDecisionSchema
from utils.role_required import citizen_or_business_required, contentieux_required
from utils.validators import ErrorMessages
from utils.email_notifier import send_dispute_resolution_notification
from datetime import datetime
from marshmallow import ValidationError

blp = Blueprint('dispute', 'dispute', url_prefix='/api/v1/disputes')

@blp.post('/')
@jwt_required()
@citizen_or_business_required
def submit_dispute():
    """Submit a dispute (Article 23)"""
    user_id = get_current_user_id()
    
    try:
        schema = DisputeSchema()
        data = schema.load(request.get_json())
    except ValidationError as err:
        return jsonify({'errors': err.messages}), 400
    
    # Convert dispute_type string to enum
    try:
        dispute_type_enum = DisputeType[data['dispute_type'].upper()]
    except (KeyError, ValueError):
        return jsonify({'errors': {'dispute_type': f"Invalid dispute type: {data['dispute_type']}. Must be one of: evaluation, calculation, exemption, penalty"}}), 400
    
    dispute = Dispute(
        claimant_id=user_id,
        dispute_type=dispute_type_enum,
        subject=data['subject'],
        description=data['description'],
        tax_id=data.get('tax_id'),
        property_id=data.get('property_id'),
        claimed_amount=data.get('claimed_amount'),
        status=DisputeStatus.SUBMITTED,
        submission_date=datetime.utcnow()
    )
    
    db.session.add(dispute)
    db.session.commit()
    
    return jsonify({
        'message': 'Dispute submitted successfully',
        'dispute_id': dispute.id,
        'status': dispute.status.value,
        'submission_date': dispute.submission_date.isoformat()
    }), 201

@blp.get('/')
@jwt_required()
def get_disputes():
    """Get disputes filtered by user role
    
    Retrieve disputes based on user's role:
    - Citizens/Businesses: Only their own disputes
    - Contentieux Officers: Assigned disputes
    - Municipal Admins: All municipal disputes
    
    ---
    responses:
      200:
        description: List of disputes
        schema:
          type: object
          properties:
            disputes:
              type: array
              items:
                type: object
                properties:
                  id:
                    type: integer
                  claimant_id:
                    type: integer
                  dispute_type:
                    type: string
                    enum: [evaluation, calculation, exemption, penalty]
                  subject:
                    type: string
                  status:
                    type: string
                    enum: [submitted, accepted, rejected, commission_review, appealed, resolved]
                  claimed_amount:
                    type: number
                  submission_date:
                    type: string
                    format: date-time
      403:
        description: Insufficient permissions
    """
    user_id = get_current_user_id()
    user = User.query.get(user_id)
    
    if user.role == UserRole.CITIZEN or user.role == UserRole.BUSINESS:
        # Get own disputes
        disputes = Dispute.query.filter_by(claimant_id=user_id).all()
    elif user.role == UserRole.CONTENTIEUX_OFFICER:
        # Get assigned disputes
        disputes = Dispute.query.filter_by(assigned_to=user_id).all()
    elif user.role == UserRole.MUNICIPAL_ADMIN:
        # Get all disputes
        disputes = Dispute.query.all()
    else:
        return jsonify({'error': ErrorMessages.ACCESS_DENIED}), 403
    
    return jsonify({
        'disputes': [{
            'id': d.id,
            'claimant_id': d.claimant_id,
            'dispute_type': d.dispute_type.value,
            'subject': d.subject,
            'status': d.status.value,
            'claimed_amount': d.claimed_amount,
            'submission_date': d.submission_date.isoformat() if d.submission_date else None,
            'commission_reviewed': d.commission_reviewed,
            'final_decision': d.final_decision
        } for d in disputes]
    }), 200

@blp.get('/office')
@jwt_required()
@contentieux_required
def get_contentieux_queue():
    """Contentieux officer view of assigned disputes
    
    Get all disputes assigned to the authenticated contentieux officer.
    Optional status filter can be applied.
    
    ---
    parameters:
      - name: status
        in: query
        type: string
        enum: [submitted, accepted, rejected, commission_review, appealed, resolved]
        description: Filter disputes by status (optional)
    responses:
      200:
        description: List of assigned disputes
        schema:
          type: object
          properties:
            disputes:
              type: array
              items:
                $ref: '#/definitions/Dispute'
      400:
        description: Invalid status filter
    """
    user_id = get_current_user_id()
    status_param = request.args.get('status')
    
    query = Dispute.query.filter_by(assigned_to=user_id)
    if status_param:
        try:
            status_enum = DisputeStatus[status_param.upper()]
        except KeyError:
            return jsonify({'error': 'Invalid status filter'}), 400
        query = query.filter_by(status=status_enum)
    
    disputes = query.order_by(Dispute.submission_date.desc()).all()
    
    return jsonify({
        'total': len(disputes),
        'disputes': [serialize_dispute(d) for d in disputes]
    }), 200

@blp.get('/<int:dispute_id>')
@jwt_required()
def get_dispute(dispute_id):
    """Get dispute details with HATEOAS links"""
    from utils.hateoas import HATEOASBuilder
    
    user_id = get_current_user_id()
    user = User.query.get(user_id)
    
    dispute = Dispute.query.get(dispute_id)
    
    if not dispute:
        return jsonify({'error': ErrorMessages.NOT_FOUND}), 404
    
    # Check access
    if user.role not in [UserRole.MUNICIPAL_ADMIN, UserRole.CONTENTIEUX_OFFICER] and dispute.claimant_id != user_id:
      return jsonify({'error': ErrorMessages.ACCESS_DENIED}), 403

    response = serialize_dispute(dispute)
    response['_links'] = HATEOASBuilder.add_dispute_links(dispute)

    return jsonify(response), 200

@blp.patch('/<int:dispute_id>/assign')
@jwt_required()
@contentieux_required
def assign_dispute(dispute_id):
    """Assign dispute to contentieux officer"""
    user_id = get_current_user_id()
    
    dispute = Dispute.query.get(dispute_id)
    
    if not dispute:
        return jsonify({'error': ErrorMessages.NOT_FOUND}), 404
    
    dispute.assigned_to = user_id
    dispute.status = DisputeStatus.ACCEPTED
    
    db.session.commit()
    
    return jsonify({
        'message': 'Dispute assigned successfully',
        'dispute_id': dispute.id,
        'assigned_to': user_id,
        'status': dispute.status.value
    }), 200

@blp.patch('/<int:dispute_id>/commission-review')
@jwt_required()
@contentieux_required
def commission_review(dispute_id):
    """Submit dispute to revision commission (Articles 24-26)
    
    Escalate a dispute to the Commission de révision for review.
    Only the assigned contentieux officer can perform this action.
    
    ---
    parameters:
      - name: dispute_id
        in: path
        type: integer
        required: true
        description: ID of the dispute to submit to commission
      - in: body
        name: body
        schema:
          type: object
          properties:
            commission_decision:
              type: string
              description: Initial notes or decision for commission review
    responses:
      200:
        description: Dispute submitted to commission successfully
        schema:
          type: object
          properties:
            message:
              type: string
            dispute_id:
              type: integer
            commission_reviewed:
              type: boolean
            status:
              type: string
      403:
        description: Not assigned to this dispute
      404:
        description: Dispute not found
    """
    user_id = get_current_user_id()
    data = request.get_json()
    
    dispute = Dispute.query.get(dispute_id)
    
    if not dispute:
        return jsonify({'error': ErrorMessages.NOT_FOUND}), 404
    
    if dispute.assigned_to != user_id:
        return jsonify({'error': ErrorMessages.ACCESS_DENIED}), 403
    
    dispute.commission_reviewed = True
    dispute.commission_review_date = datetime.utcnow()
    dispute.commission_decision = data.get('commission_decision')
    dispute.status = DisputeStatus.COMMISSION_REVIEW
    
    db.session.commit()
    
    return jsonify({
        'message': 'Commission review submitted',
        'dispute_id': dispute.id,
        'commission_reviewed': True,
        'status': dispute.status.value
    }), 200

@blp.patch('/<int:dispute_id>/assign')
@jwt_required()
@contentieux_required
def make_decision(dispute_id):
    """Make final decision on dispute
    
    Record the final contentieux decision on a dispute case.
    This closes the dispute and may adjust tax amounts.
    
    ---
    parameters:
      - name: dispute_id
        in: path
        type: integer
        required: true
        description: ID of the dispute
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - final_decision
          properties:
            final_decision:
              type: string
              description: Detailed final decision text
            final_amount:
              type: number
              format: float
              description: Adjusted tax amount (if applicable)
    responses:
      200:
        description: Decision recorded successfully
        schema:
          type: object
          properties:
            message:
              type: string
            dispute_id:
              type: integer
            final_decision:
              type: string
            final_amount:
              type: number
            status:
              type: string
      400:
        description: Invalid input data
      403:
        description: Not assigned to this dispute
      404:
        description: Dispute not found
    """
    user_id = get_current_user_id()
    
    try:
        schema = DisputeDecisionSchema()
        data = schema.load(request.get_json())
    except ValidationError as err:
        return jsonify({'errors': err.messages}), 400
    
    dispute = Dispute.query.get(dispute_id)
    
    if not dispute:
        return jsonify({'error': ErrorMessages.NOT_FOUND}), 404
    
    if dispute.assigned_to != user_id:
        return jsonify({'error': ErrorMessages.ACCESS_DENIED}), 403
    
    dispute.final_decision = data['final_decision']
    dispute.final_amount = data.get('final_amount')
    dispute.decision_date = datetime.utcnow()
    dispute.status = DisputeStatus.RESOLVED
    
    db.session.commit()
    
    # Send dispute resolution notification email
    claimant = User.query.get(dispute.claimant_id)
    if claimant and claimant.email:
        send_dispute_resolution_notification(
            user_email=claimant.email,
            user_name=claimant.first_name or claimant.username,
            dispute_id=str(dispute.id),
            resolution_status=data['final_decision'],
            notes=data.get('notes')
        )
    
    return jsonify({
        'message': 'Final decision recorded',
        'dispute_id': dispute.id,
        'final_decision': dispute.final_decision,
        'final_amount': dispute.final_amount,
        'status': dispute.status.value
    }), 200

def serialize_dispute(dispute: Dispute):
    """Serialize dispute for JSON responses."""
    return {
        'id': dispute.id,
        'claimant_id': dispute.claimant_id,
        'dispute_type': dispute.dispute_type.value,
        'subject': dispute.subject,
        'description': dispute.description,
        'tax_id': dispute.tax_id,
        'property_id': dispute.property_id,
        'claimed_amount': dispute.claimed_amount,
        'status': dispute.status.value,
        'assigned_to': dispute.assigned_to,
        'submission_date': dispute.submission_date.isoformat() if dispute.submission_date else None,
        'commission_reviewed': dispute.commission_reviewed,
        'commission_review_date': dispute.commission_review_date.isoformat() if dispute.commission_review_date else None,
        'commission_decision': dispute.commission_decision,
        'final_decision': dispute.final_decision,
        'final_amount': dispute.final_amount,
        'decision_date': dispute.decision_date.isoformat() if dispute.decision_date else None
    }
@blp.post('/<int:dispute_id>/appeal')
@jwt_required()
@citizen_or_business_required
def appeal_dispute(dispute_id):
    """Appeal the final decision on a resolved dispute
    
    File an appeal against the contentieux decision.
    Can only appeal disputes that have been resolved.
    
    ---
    parameters:
      - name: dispute_id
        in: path
        type: integer
        required: true
        description: ID of the resolved dispute to appeal
      - in: body
        name: body
        schema:
          type: object
          properties:
            reason:
              type: string
              description: Reason for appealing the decision
    responses:
      201:
        description: Appeal filed successfully
        schema:
          type: object
          properties:
            message:
              type: string
            dispute_id:
              type: integer
            appeal_date:
              type: string
              format: date-time
            status:
              type: string
      400:
        description: Cannot appeal (wrong status or already appealed)
      403:
        description: Not the dispute claimant
      404:
        description: Dispute not found
    """
    user_id = get_current_user_id()
    data = request.get_json()
    
    dispute = Dispute.query.get(dispute_id)
    
    if not dispute:
        return jsonify({'error': ErrorMessages.NOT_FOUND}), 404
    
    if dispute.claimant_id != user_id:
        return jsonify({'error': ErrorMessages.ACCESS_DENIED}), 403
    
    if dispute.status != DisputeStatus.RESOLVED:
        return jsonify({'error': 'Can only appeal resolved disputes'}), 400
    
    if dispute.appeal_filed:
        return jsonify({'error': 'Appeal already filed for this dispute'}), 400
    
    dispute.appeal_filed = True
    dispute.appeal_date = datetime.utcnow()
    dispute.appeal_reason = data.get('reason')
    dispute.status = DisputeStatus.APPEALED
    
    db.session.commit()
    
    return jsonify({
        'message': 'Appeal filed successfully',
        'dispute_id': dispute_id,
        'appeal_date': dispute.appeal_date.isoformat(),
        'status': dispute.status.value
    }), 201
