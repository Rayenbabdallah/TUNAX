"""Budget voting model for participatory budget"""
from extensions.db import db
from datetime import datetime
from enum import Enum

class BudgetProjectStatus(Enum):
    DRAFT = "draft"
    OPEN_FOR_VOTING = "open_for_voting"
    CLOSED = "closed"
    APPROVED = "approved"
    REJECTED = "rejected"

class BudgetProject(db.Model):
    __tablename__ = 'budget_projects'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Project details
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    budget_amount = db.Column(db.Float, nullable=False)
    commune_id = db.Column(db.Integer, db.ForeignKey('commune.id'), nullable=True)
    
    # Status
    status = db.Column(db.Enum(BudgetProjectStatus), default=BudgetProjectStatus.DRAFT)
    
    # Voting period
    voting_start = db.Column(db.DateTime)
    voting_end = db.Column(db.DateTime)
    
    # Created by
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))  # Admin
    
    # Votes
    total_votes = db.Column(db.Integer, default=0)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    votes = db.relationship('BudgetVote', backref='project', lazy=True, cascade='all, delete-orphan')
    commune = db.relationship('Commune', backref='budget_projects')
    
    def __repr__(self):
        return f'<BudgetProject {self.id}>'

class BudgetVote(db.Model):
    __tablename__ = 'budget_votes'
    
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('budget_projects.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    weight = db.Column(db.Integer, nullable=False, default=1)
    
    # Anonymous voting
    voted_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Unique constraint to prevent duplicate votes
    __table_args__ = (db.UniqueConstraint('project_id', 'user_id', name='unique_project_user_vote'),)
    
    def __repr__(self):
        return f'<BudgetVote project={self.project_id} user={self.user_id} weight={self.weight}>'
