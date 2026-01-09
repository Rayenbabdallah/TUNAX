"""Models package initialization"""
from .user import User, UserRole
from .commune import Commune
from .municipal_config import MunicipalReferencePrice, MunicipalServiceConfig, DocumentRequirement
from .property import Property, PropertyStatus, PropertyAffectation
from .land import Land, LandStatus, LandType
from .tax import Tax, TaxType, TaxStatus
from .penalty import Penalty, PenaltyType, PenaltyStatus
from .dispute import Dispute, DisputeStatus, DisputeType
from .payment import Payment, PaymentStatus, PaymentMethod
from .payment_plan import PaymentPlan, PaymentPlanStatus
from .permit import Permit, PermitType, PermitStatus
from .inspection import Inspection, InspectionStatus
from .reclamation import Reclamation, ReclamationType, ReclamationStatus
from .budget import BudgetProject, BudgetVote, BudgetProjectStatus
from .declaration import Declaration, DeclarationType
from .document import Document, DocumentType, DocumentStatus
from .satellite_verification import SatelliteVerification

__all__ = [
    'User', 'UserRole',
    'Commune',
    'MunicipalReferencePrice', 'MunicipalServiceConfig', 'DocumentRequirement',
    'Property', 'PropertyStatus', 'PropertyAffectation',
    'Land', 'LandStatus', 'LandType',
    'Tax', 'TaxType', 'TaxStatus',
    'Penalty', 'PenaltyType', 'PenaltyStatus',
    'Dispute', 'DisputeStatus', 'DisputeType',
    'Payment', 'PaymentStatus', 'PaymentMethod',
    'PaymentPlan', 'PaymentPlanStatus',
    'Permit', 'PermitType', 'PermitStatus',
    'Inspection', 'InspectionStatus',
    'Reclamation', 'ReclamationType', 'ReclamationStatus',
    'BudgetProject', 'BudgetVote', 'BudgetProjectStatus',
    'Declaration', 'DeclarationType',
    'Document', 'DocumentType', 'DocumentStatus',
    'SatelliteVerification'
]
