"""Marshmallow schemas for request/response validation"""
from marshmallow import Schema, fields, validate, validates, ValidationError
from utils.validators import Validators

class UserRegisterSchema(Schema):
    """Schema for user registration"""
    username = fields.Str(required=True, validate=validate.Length(min=3, max=80))
    email = fields.Email(required=True)
    password = fields.Str(required=True, validate=validate.Length(min=8))
    first_name = fields.Str(allow_none=True)
    last_name = fields.Str(allow_none=True)
    phone = fields.Str(allow_none=True)
    cin = fields.Str(allow_none=True)
    
    # Business-specific
    business_name = fields.Str(allow_none=True)
    business_registration = fields.Str(allow_none=True)

class UserLoginSchema(Schema):
    """Schema for user login"""
    username = fields.Str(required=True)
    password = fields.Str(required=True)

class PropertySchema(Schema):
    """Schema for property declaration"""
    street_address = fields.Str(required=True)
    city = fields.Str(required=True)
    delegation = fields.Str(allow_none=True)
    post_code = fields.Str(allow_none=True)
    latitude = fields.Float(allow_none=True)
    longitude = fields.Float(allow_none=True)
    
    # Property details
    surface_couverte = fields.Float(required=True, validate=validate.Range(min=1))
    surface_totale = fields.Float(allow_none=True)
    affectation = fields.Str(required=True, validate=validate.OneOf(
        ['residential', 'commercial', 'industrial', 'agricultural', 'administrative']
    ))
    nb_floors = fields.Int(allow_none=True)
    nb_rooms = fields.Int(allow_none=True)
    construction_year = fields.Int(allow_none=True)
    
    # Tax details
    reference_price = fields.Float(required=True, validate=validate.Range(min=0))
    tax_rate_category = fields.Int(allow_none=True)
    service_rate = fields.Int(validate=validate.Range(min=0, max=4), allow_none=True)
    
    # Exemptions
    is_exempt = fields.Bool(allow_none=True)
    exemption_reason = fields.Str(allow_none=True)

class LandSchema(Schema):
    """Schema for land declaration"""
    street_address = fields.Str(required=True)
    city = fields.Str(required=True)
    delegation = fields.Str(allow_none=True)
    post_code = fields.Str(allow_none=True)
    latitude = fields.Float(allow_none=True)
    longitude = fields.Float(allow_none=True)
    
    # Land details
    surface = fields.Float(required=True, validate=validate.Range(min=1))
    land_type = fields.Str(required=True, validate=validate.OneOf(
        ['agricultural', 'commercial', 'industrial', 'buildable', 'other']
    ))
    
    # Tax details
    vénale_value = fields.Float(allow_none=True)
    tariff_value = fields.Float(allow_none=True)
    
    # Exemptions
    is_exempt = fields.Bool(allow_none=True)
    exemption_reason = fields.Str(allow_none=True)

class TaxSchema(Schema):
    """Schema for tax data"""
    id = fields.Int(dump_only=True)
    tax_type = fields.Str()
    tax_year = fields.Int()
    base_amount = fields.Float()
    rate_percent = fields.Float()
    tax_amount = fields.Float()
    penalty_amount = fields.Float()
    total_amount = fields.Float()
    status = fields.Str()

class PaymentSchema(Schema):
    """Schema for payment"""
    amount = fields.Float(required=True, validate=validate.Range(min=0.01))
    method = fields.Str(required=True, validate=validate.OneOf(
        ['card', 'bank_transfer', 'check', 'cash']
    ))
    tax_id = fields.Int(allow_none=True)

class DisputeSchema(Schema):
    """Schema for dispute submission"""
    dispute_type = fields.Str(required=True, validate=validate.OneOf(
        ['evaluation', 'calculation', 'exemption', 'penalty']
    ))
    subject = fields.Str(required=True)
    description = fields.Str(required=True)
    tax_id = fields.Int(allow_none=True)
    property_id = fields.Int(allow_none=True)
    claimed_amount = fields.Float(allow_none=True)

class DisputeDecisionSchema(Schema):
    """Schema for dispute decision"""
    final_decision = fields.Str(required=True)
    final_amount = fields.Float(allow_none=True)

class PermitSchema(Schema):
    """Schema for permit request"""
    permit_type = fields.Str(required=True, validate=validate.OneOf(
        ['construction', 'lotissement', 'occupancy', 'signature_legalization']
    ))
    property_id = fields.Int(allow_none=True)
    description = fields.Str(allow_none=True)

class PermitDecisionSchema(Schema):
    """Schema for permit decision"""
    status = fields.Str(required=True, validate=validate.OneOf(
        ['approved', 'rejected', 'blocked_unpaid_taxes']
    ))
    notes = fields.Str(allow_none=True)

class InspectionReportSchema(Schema):
    """Schema for inspection report"""
    property_id = fields.Int(allow_none=True)
    land_id = fields.Int(allow_none=True)
    notes = fields.Str()
    satellite_verified = fields.Bool()
    discrepancies_found = fields.Bool()
    evidence_urls = fields.List(fields.Str(), allow_none=True)
    recommendation = fields.Str(allow_none=True)

class ReclamationSchema(Schema):
    """Schema for service reclamation"""
    reclamation_type = fields.Str(required=True, validate=validate.OneOf(
        ['lighting', 'road_maintenance', 'drainage', 'waste_collection', 'water', 'other']
    ))
    street_address = fields.Str(required=True)
    city = fields.Str(required=True)
    description = fields.Str(required=True)
    priority = fields.Str(allow_none=True, validate=validate.OneOf(
        ['low', 'medium', 'high']
    ))

class BudgetProjectSchema(Schema):
    """Schema for budget project"""
    title = fields.Str(required=True)
    description = fields.Str(allow_none=True)
    budget_amount = fields.Float(required=True, validate=validate.Range(min=1))
    commune_id = fields.Int(allow_none=True)

class BudgetVoteSchema(Schema):
    """Schema for budget vote"""
    project_id = fields.Int(required=True)

class AddressValidationSchema(Schema):
    """Schema for address validation"""
    street = fields.Str(required=True)
    city = fields.Str(required=True)
