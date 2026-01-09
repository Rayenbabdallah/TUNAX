from marshmallow import Schema, fields

class UserRegisterCitizenSchema(Schema):
    username = fields.Str(required=True)
    email = fields.Email(required=True)
    password = fields.Str(required=True)
    first_name = fields.Str()
    last_name = fields.Str()
    phone = fields.Str()
    cin = fields.Str()
    commune_id = fields.Int()  # Optional: citizen can register with specific commune

class UserRegisterBusinessSchema(Schema):
    username = fields.Str(required=True)
    email = fields.Email(required=True)
    password = fields.Str(required=True)
    first_name = fields.Str()
    last_name = fields.Str()
    phone = fields.Str()
    business_name = fields.Str()
    business_registration = fields.Str()
    commune_id = fields.Int()  # Optional: business can register with specific commune

class LoginSchema(Schema):
    username = fields.Str(required=True)
    password = fields.Str(required=True)

class TokenSchema(Schema):
    access_token = fields.Str()
    refresh_token = fields.Str()
    role = fields.Str()
    redirect_to = fields.Str()
    commune_id = fields.Int()  # Include commune_id in token response for municipal users
