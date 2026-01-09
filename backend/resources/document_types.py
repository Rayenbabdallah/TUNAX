"""Document type management (municipal admin configurable)."""
from flask import jsonify, request
from flask_smorest import Blueprint
from flask_jwt_extended import jwt_required
from extensions.db import db
from models import DocumentType
from utils.jwt_helpers import get_current_user_id
from utils.role_required import municipal_admin_required
from marshmallow import Schema, fields


blp = Blueprint("document_types", "document_types", url_prefix="/api/v1/document-types")
document_types_bp = blp


class DocumentTypeCreateSchema(Schema):
    """Schema for creating document types"""
    code = fields.Str(required=True)
    name = fields.Str(required=True)
    required = fields.Bool(allow_none=True, missing=False)


class DocumentTypeUpdateSchema(Schema):
    """Schema for updating document types"""
    name = fields.Str(allow_none=True)
    required = fields.Bool(allow_none=True)


@blp.get("")
@blp.response(200)
@jwt_required()
@municipal_admin_required
def list_document_types():
    """List document types for the admin's municipality."""
    from flask_jwt_extended import get_jwt

    admin_commune_id = get_jwt().get("commune_id")
    types = DocumentType.query.filter_by(commune_id=admin_commune_id).order_by(DocumentType.code).all()

    return jsonify(
        {
            "document_types": [
                {
                    "id": t.id,
                    "code": t.code,
                    "label": t.label,
                    "description": t.description,
                    "is_required": t.is_required,
                    "is_active": t.is_active,
                }
                for t in types
            ]
        }
    ), 200


@blp.post("")
@blp.arguments(DocumentTypeCreateSchema, location="json")
@blp.response(201)
@jwt_required()
@municipal_admin_required
def create_document_type(data):
    """Create a new document type within the admin's municipality."""
    from flask_jwt_extended import get_jwt

    admin_commune_id = get_jwt().get("commune_id")
    data = request.get_json() or {}

    code = (data.get("code") or "").upper().strip()
    label = (data.get("label") or "").strip()

    if not code or not label:
        return jsonify({"error": "code and label are required"}), 400

    existing = DocumentType.query.filter_by(
        commune_id=admin_commune_id, code=code
    ).first()
    if existing:
        return jsonify({"error": "Document type code already exists"}), 400

    doc_type = DocumentType(
        code=code,
        label=label,
        description=data.get("description"),
        is_required=bool(data.get("is_required", False)),
        is_active=bool(data.get("is_active", True)),
        commune_id=admin_commune_id,
        created_by=get_current_user_id(),
    )

    db.session.add(doc_type)
    db.session.commit()

    return jsonify(
        {
            "message": "Document type created",
            "id": doc_type.id,
            "code": doc_type.code,
        }
    ), 201


@blp.patch("/<int:type_id>")
@blp.arguments(DocumentTypeUpdateSchema, location="json")
@blp.response(200)
@jwt_required()
@municipal_admin_required
def update_document_type(data, type_id):
    """Update label/flags of a document type (same municipality)."""
    from flask_jwt_extended import get_jwt

    admin_commune_id = get_jwt().get("commune_id")
    doc_type = DocumentType.query.get(type_id)

    if not doc_type or doc_type.commune_id != admin_commune_id:
        return jsonify({"error": "Document type not found"}), 404

    data = request.get_json() or {}

    if "label" in data:
        doc_type.label = data.get("label") or doc_type.label
    if "description" in data:
        doc_type.description = data.get("description")
    if "is_required" in data:
        doc_type.is_required = bool(data.get("is_required"))
    if "is_active" in data:
        doc_type.is_active = bool(data.get("is_active"))

    db.session.commit()

    return jsonify(
        {
            "message": "Document type updated",
            "id": doc_type.id,
            "is_required": doc_type.is_required,
            "is_active": doc_type.is_active,
        }
    ), 200
