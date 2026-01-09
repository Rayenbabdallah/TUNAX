"""Participatory budget voting routes"""
from flask import jsonify, request
from flask_smorest import Blueprint
from flask_jwt_extended import jwt_required
from utils.jwt_helpers import get_current_user_id
from extensions.db import db
from models.user import User, UserRole
from models.budget import BudgetProject, BudgetProjectStatus, BudgetVote
from models.property import Property
from models.land import Land
from models import Commune
from schemas import BudgetProjectSchema, BudgetVoteSchema
from utils.role_required import admin_required, citizen_or_business_required
from utils.validators import ErrorMessages
from marshmallow import Schema, fields
from datetime import datetime, timedelta

blp = Blueprint('budget', 'budget', url_prefix='/api/v1/budget', description='Budget voting operations')
budget_bp = blp


class BudgetProjectCreateSchema(Schema):
    """Schema for creating budget projects"""
    title = fields.Str(required=True)
    description = fields.Str()
    budget_amount = fields.Float(required=True)
    commune_id = fields.Int()


class BudgetProjectUpdateSchema(Schema):
    """Schema for updating budget project voting duration"""
    voting_duration_days = fields.Int()


class BudgetProjectResponseSchema(Schema):
    """Schema for budget project response"""
    id = fields.Int()
    title = fields.Str()
    description = fields.Str()
    budget_amount = fields.Float()
    commune_id = fields.Int()
    commune_name = fields.Str()
    status = fields.Str()
    total_votes = fields.Int()
    voting_start = fields.DateTime()
    voting_end = fields.DateTime()
    created_by = fields.Int()
    created_at = fields.DateTime()


def _resolve_project_commune(data, creator: User):
    """Determine which commune the project belongs to."""
    requested_commune_id = data.get('commune_id')
    commune_id = requested_commune_id or creator.commune_id
    if not commune_id:
        return None
    return Commune.query.get(commune_id)


def _count_assets_in_commune(user_id: int, commune_id: int) -> int:
    """Return how many properties/lands the user owns in the target commune."""
    if not commune_id:
        return 0
    tib_count = Property.query.filter_by(owner_id=user_id, commune_id=commune_id).count()
    land_count = Land.query.filter_by(owner_id=user_id, commune_id=commune_id).count()
    return tib_count + land_count

@blp.post('/projects')
@jwt_required()
@admin_required
@blp.arguments(BudgetProjectCreateSchema, location="json")
@blp.response(201, BudgetProjectResponseSchema)
def create_budget_project(data):
    """Create a new budget project for voting"""
    user_id = get_current_user_id()
    creator = User.query.get(user_id)
    if not creator:
        return {'error': ErrorMessages.NOT_FOUND, 'message': 'User not found'}, 404

    commune = _resolve_project_commune(data, creator)
    if not commune:
        return jsonify({
            'error': 'Commune required',
            'message': 'Provide commune_id or create the project from a municipal admin account'
        }), 400
    
    project = BudgetProject(
        title=data['title'],
        description=data.get('description'),
        budget_amount=data['budget_amount'],
        status=BudgetProjectStatus.DRAFT,
        created_by=user_id,
        created_at=datetime.utcnow(),
        commune_id=commune.id
    )
    
    db.session.add(project)
    db.session.commit()
    
    return jsonify({
        'message': 'Budget project created',
        'project_id': project.id,
        'title': project.title,
        'budget_amount': project.budget_amount,
        'commune_id': project.commune_id,
        'commune_name': commune.nom_municipalite_fr if commune else None
    }), 201

@budget_bp.get('/projects')
@jwt_required()
def get_budget_projects():
    """Get budget projects"""
    status = request.args.get('status')
    
    query = BudgetProject.query
    
    if status:
        try:
            query = query.filter_by(status=BudgetProjectStatus[status.upper()])
        except KeyError:
            return jsonify({'error': 'Invalid status filter'}), 400
    
    commune_id = request.args.get('commune_id', type=int)
    if commune_id:
        query = query.filter_by(commune_id=commune_id)
    
    projects = query.all()
    
    return jsonify({
        'total': len(projects),
        'projects': [{
            'id': p.id,
            'title': p.title,
            'description': p.description,
            'budget_amount': p.budget_amount,
            'commune_id': p.commune_id,
            'commune_name': p.commune.nom_municipalite_fr if p.commune else None,
            'status': p.status.value,
            'total_votes': p.total_votes,
            'voting_start': p.voting_start.isoformat() if p.voting_start else None,
            'voting_end': p.voting_end.isoformat() if p.voting_end else None
        } for p in projects]
    }), 200

@budget_bp.get('/projects/<int:project_id>')
@jwt_required()
def get_budget_project(project_id):
    """Get budget project details"""
    project = BudgetProject.query.get(project_id)
    
    if not project:
        return jsonify({'error': ErrorMessages.NOT_FOUND}), 404
    
    return jsonify({
        'id': project.id,
        'title': project.title,
        'description': project.description,
        'budget_amount': project.budget_amount,
        'commune_id': project.commune_id,
        'commune_name': project.commune.nom_municipalite_fr if project.commune else None,
        'status': project.status.value,
        'total_votes': project.total_votes,
        'voting_start': project.voting_start.isoformat() if project.voting_start else None,
        'voting_end': project.voting_end.isoformat() if project.voting_end else None,
        'created_by': project.created_by,
        'created_at': project.created_at.isoformat() if project.created_at else None
    }), 200

@budget_bp.patch('/projects/<int:project_id>/open-voting')
@jwt_required()
@admin_required
def open_voting(project_id):
    """Open voting for budget project"""
    data = request.get_json()
    
    project = BudgetProject.query.get(project_id)
    
    if not project:
        return jsonify({'error': ErrorMessages.NOT_FOUND}), 404
    
    project.status = BudgetProjectStatus.OPEN_FOR_VOTING
    project.voting_start = datetime.utcnow()
    
    if data.get('voting_duration_days'):
        from datetime import timedelta
        project.voting_end = datetime.utcnow() + timedelta(days=data['voting_duration_days'])
    
    db.session.commit()
    
    return jsonify({
        'message': 'Voting opened',
        'project_id': project_id,
        'status': project.status.value,
        'voting_start': project.voting_start.isoformat()
    }), 200

@budget_bp.post('/projects/<int:project_id>/vote')
@jwt_required()
@citizen_or_business_required
def vote_on_project(project_id):
    """Vote for a budget project"""
    user_id = get_current_user_id()
    
    project = BudgetProject.query.get(project_id)
    
    if not project:
        return jsonify({'error': ErrorMessages.NOT_FOUND}), 404
    
    if not project.commune_id:
        return jsonify({'error': 'Project missing commune association'}), 400
    
    # Check if voting is open
    if project.status != BudgetProjectStatus.OPEN_FOR_VOTING:
        return jsonify({'error': 'Voting is not currently open for this project'}), 400
    
    # Check if voting deadline passed
    if project.voting_end and project.voting_end < datetime.utcnow():
        return jsonify({'error': 'Voting period has ended'}), 400
    
    # Check if user already voted
    existing_vote = BudgetVote.query.filter_by(
        project_id=project_id,
        user_id=user_id
    ).first()
    
    if existing_vote:
        return jsonify({'error': 'You have already voted for this project'}), 400

    vote_weight = _count_assets_in_commune(user_id, project.commune_id)
    if vote_weight <= 0:
        return jsonify({
            'error': 'Not eligible to vote',
            'message': 'You do not own any declared properties or lands in this municipality.'
        }), 400
    
    # Create vote (anonymous - user identity not visible)
    vote = BudgetVote(
        project_id=project_id,
        user_id=user_id,
        weight=vote_weight,
        voted_at=datetime.utcnow()
    )
    
    # Increment project vote count
    project.total_votes += vote_weight
    
    db.session.add(vote)
    db.session.commit()
    
    return jsonify({
        'message': 'Vote recorded (anonymous)',
        'project_id': project_id,
        'weight': vote_weight,
        'total_votes': project.total_votes
    }), 201

@budget_bp.get('/projects/<int:project_id>/votes')
@jwt_required()
@admin_required
def get_project_votes(project_id):
    """Get vote count for project"""
    project = BudgetProject.query.get(project_id)
    
    if not project:
        return jsonify({'error': ErrorMessages.NOT_FOUND}), 404
    
    vote_rows = [{
        'user_id': v.user_id,
        'weight': v.weight,
        'voted_at': v.voted_at.isoformat() if v.voted_at else None
    } for v in project.votes]
    
    return jsonify({
        'project_id': project_id,
        'title': project.title,
        'total_votes': project.total_votes,
        'status': project.status.value,
        'commune_id': project.commune_id,
        'votes': vote_rows
    }), 200

@budget_bp.patch('/projects/<int:project_id>/close-voting')
@jwt_required()
@admin_required
def close_voting(project_id):
    """Close voting for budget project"""
    project = BudgetProject.query.get(project_id)
    
    if not project:
        return jsonify({'error': ErrorMessages.NOT_FOUND}), 404
    
    project.status = BudgetProjectStatus.CLOSED
    project.voting_end = datetime.utcnow()
    
    db.session.commit()
    
    return jsonify({
        'message': 'Voting closed',
        'project_id': project_id,
        'total_votes': project.total_votes,
        'status': project.status.value
    }), 200

@budget_bp.patch('/projects/<int:project_id>/approve')
@jwt_required()
@admin_required
def approve_project(project_id):
    """Approve budget project"""
    project = BudgetProject.query.get(project_id)
    
    if not project:
        return jsonify({'error': ErrorMessages.NOT_FOUND}), 404
    
    project.status = BudgetProjectStatus.APPROVED
    
    db.session.commit()
    
    return jsonify({
        'message': 'Project approved',
        'project_id': project_id,
        'status': project.status.value
    }), 200

@budget_bp.get('/voting-history')
@jwt_required()
@citizen_or_business_required
def get_voting_history():
    """Get user's voting history"""
    user_id = get_current_user_id()
    
    votes = BudgetVote.query.filter_by(user_id=user_id).all()
    
    return jsonify({
        'total_votes': sum(v.weight for v in votes),
        'votes': [{
            'project_id': v.project_id,
            'project_title': v.project.title,
            'weight': v.weight,
            'voted_at': v.voted_at.isoformat() if v.voted_at else None
        } for v in votes]
    }), 200
