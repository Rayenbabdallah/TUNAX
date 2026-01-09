from marshmallow import Schema, fields, validate

class PropertyCreateSchema(Schema):
    commune_id = fields.Int(required=True)
    street_address = fields.Str(required=True)
    city = fields.Str(required=True)
    delegation = fields.Str()
    post_code = fields.Str()
    latitude = fields.Float()
    longitude = fields.Float()
    surface_couverte = fields.Float(required=True)
    surface_totale = fields.Float()
    affectation = fields.Str(required=True)
    nb_floors = fields.Int()
    nb_rooms = fields.Int()
    construction_year = fields.Int()
    urban_zone = fields.Str()
    reference_price = fields.Float()
    reference_price_per_m2 = fields.Float()
    service_rate = fields.Int()
    is_exempt = fields.Bool()
    exemption_reason = fields.Str()
    # Structured address fields
    address_mode = fields.Str()
    street_name = fields.Str()
    villa_number = fields.Str()
    residence_name = fields.Str()
    apartment_number = fields.Str()
    locality = fields.Str()

class TaxResultSchema(Schema):
    base_amount = fields.Float()
    rate_percent = fields.Float()
    tax_amount = fields.Float()
    total_amount = fields.Float()
    surface_multiplier = fields.Float()
    service_rate = fields.Float()
    penalty_amount = fields.Float()

class PropertySchema(PropertyCreateSchema):
    id = fields.Int()
    owner_id = fields.Int()
    status = fields.Str()
    satellite_verified = fields.Bool()
    satellite_verification_date = fields.DateTime()
    created_at = fields.DateTime()
    tax = fields.Nested(TaxResultSchema)

class LandCreateSchema(Schema):
    commune_id = fields.Int(required=True)
    street_address = fields.Str(required=True)
    city = fields.Str(required=True)
    delegation = fields.Str()
    latitude = fields.Float()
    longitude = fields.Float()
    surface = fields.Float(required=True)
    land_type = fields.Str(required=True)
    urban_zone = fields.Str()
    venale_value = fields.Float()
    tariff_value = fields.Float()
    is_exempt = fields.Bool()
    exemption_reason = fields.Str()
    # Structured address fields
    address_mode = fields.Str()
    street_name = fields.Str()
    villa_number = fields.Str()
    residence_name = fields.Str()
    apartment_number = fields.Str()
    locality = fields.Str()

class LandSchema(LandCreateSchema):
    id = fields.Int()
    owner_id = fields.Int()
    latitude = fields.Float()
    longitude = fields.Float()
    status = fields.Str()
    satellite_verified = fields.Bool()
    created_at = fields.DateTime()
    tax = fields.Nested(TaxResultSchema)

class PaymentCreateSchema(Schema):
    tax_id = fields.Int(required=True)
    amount = fields.Float(required=True)
    method = fields.Str(required=True, validate=validate.OneOf(['card', 'bank_transfer', 'cash', 'e_dinar']))

class PaymentSchema(PaymentCreateSchema):
    id = fields.Int()
    user_id = fields.Int()
    status = fields.Str()
    reference_number = fields.Str()
    payment_date = fields.DateTime()

class AttestationSchema(Schema):
    attestation_number = fields.Str()
    user_id = fields.Int()
    issued_date = fields.DateTime()
    status = fields.Str()
    message = fields.Str()

class PermitRequestSchema(Schema):
    permit_type = fields.Str(required=True, validate=validate.OneOf(['construction', 'occupation', 'demolition', 'subdivision']))
    property_id = fields.Int()
    description = fields.Str()

class PermitStatusSchema(Schema):
    user_id = fields.Int()
    eligible_for_permit = fields.Bool()
    unpaid_taxes = fields.Int()
    total_due = fields.Float()

class PermitSchema(PermitRequestSchema):
    id = fields.Int()
    user_id = fields.Int()
    status = fields.Str()
    submitted_date = fields.DateTime()
    decision_date = fields.DateTime()
    notes = fields.Str()
    taxes_paid = fields.Bool()

class PermitDecisionSchema(Schema):
    status = fields.Str(required=True, validate=validate.OneOf(['approved', 'rejected', 'blocked']))
    notes = fields.Str()
