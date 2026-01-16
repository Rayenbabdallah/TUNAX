"""Document management routes aligned with Tunisian local taxation workflow."""
import os
from datetime import datetime
from flask import jsonify, request, current_app, send_file
from flask_smorest import Blueprint
from flask_jwt_extended import jwt_required, get_jwt
from werkzeug.utils import secure_filename
from extensions.db import db
from utils.jwt_helpers import get_current_user_id
from utils.role_required import role_required
from models import (
    Document,
    DocumentStatus,
    DocumentType,
    Declaration,
    UserRole,
)
from marshmallow import Schema, fields

blp = Blueprint("documents", "documents", url_prefix="/api/v1/documents")
documents_bp = blp


class DocumentUploadSchema(Schema):
    """Schema for document uploads"""
    file = fields.Field(required=True)
    document_type_id = fields.Int(required=True)


class DocumentReviewSchema(Schema):
    """Schema for document review"""
    status = fields.Str(required=True)
    notes = fields.Str(allow_none=True)


ALLOWED_MIME_TYPES = {"application/pdf", "image/jpeg", "image/png"}
DEFAULT_MAX_MB = 10


def _get_commune_and_role():
    claims = get_jwt()
    return claims.get("commune_id"), claims.get("role")


def _validate_upload_file(file_obj, max_mb):
    if not file_obj:
        return "File is required"
    if file_obj.mimetype not in ALLOWED_MIME_TYPES:
        return "Invalid file type. Allowed: PDF, JPG, PNG"
    file_obj.seek(0, os.SEEK_END)
    size_bytes = file_obj.tell()
    file_obj.seek(0)
    if size_bytes > max_mb * 1024 * 1024:
        return f"File exceeds {max_mb}MB limit"
    return None


@blp.post("/declarations/<int:declaration_id>/documents")
@blp.response(201)
@jwt_required()
@role_required(UserRole.CITIZEN, UserRole.BUSINESS)
def upload_document(declaration_id):
    """Upload a supporting document for a declaration (citizen/business only)."""

    uploader_id = get_current_user_id()
    declaration = Declaration.query.get(declaration_id)
    if not declaration:
        return jsonify({"error": "Declaration not found"}), 404

    if declaration.owner_id != uploader_id:
        return jsonify({"error": "Access denied"}), 403

    # Configurable upload constraints
    max_mb = current_app.config.get("MAX_DOCUMENT_UPLOAD_MB", DEFAULT_MAX_MB)
    storage_root = current_app.config.get("DOCUMENTS_STORAGE_PATH", "storage/documents")

    document_type_code = request.form.get("documentType")
    document_type_id = request.form.get("documentTypeId")
    issue_date_raw = request.form.get("issueDate")
    file_obj = request.files.get("file")

    # Validate type
    doc_type = None
    if document_type_id:
        doc_type = DocumentType.query.filter_by(
            id=int(document_type_id),
            commune_id=declaration.commune_id,
            is_active=True,
        ).first()
    elif document_type_code:
        doc_type = DocumentType.query.filter_by(
            code=document_type_code.upper(),
            commune_id=declaration.commune_id,
            is_active=True,
        ).first()

    if not doc_type:
        return jsonify({"error": "Invalid or inactive document type"}), 400

    # Validate file
    err = _validate_upload_file(file_obj, max_mb)
    if err:
        return jsonify({"error": err}), 400

    safe_name = secure_filename(file_obj.filename)
    ext = os.path.splitext(safe_name)[1]
    storage_dir = os.path.join(storage_root, str(declaration_id))
    os.makedirs(storage_dir, exist_ok=True)
    storage_key = f"{datetime.utcnow().strftime('%Y%m%d%H%M%S%f')}_{safe_name}"
    storage_path = os.path.join(storage_dir, storage_key)
    file_obj.save(storage_path)

    issue_date = None
    if issue_date_raw:
        try:
            issue_date = datetime.fromisoformat(issue_date_raw).date()
        except ValueError:
            return jsonify({"error": "Invalid issueDate format (use ISO 8601)"}), 400

    # Versioning: increment within declaration + type
    last_doc = (
        Document.query.filter_by(
            declaration_id=declaration_id, document_type_id=doc_type.id
        )
        .order_by(Document.version.desc())
        .first()
    )
    new_version = (last_doc.version if last_doc else 0) + 1

    document = Document(
        declaration_id=declaration_id,
        document_type_id=doc_type.id,
        uploader_id=uploader_id,
        storage_path=storage_path,
        file_name=safe_name,
        mime_type=file_obj.mimetype,
        file_size=os.path.getsize(storage_path),
        issue_date=issue_date,
        status=DocumentStatus.PENDING,
        version=new_version,
        previous_version_id=last_doc.id if last_doc else None,
    )

    db.session.add(document)
    db.session.commit()

    return jsonify(
        {
            "message": "Document uploaded",
            "document_id": document.id,
            "status": document.status.value,
            "version": document.version,
            "uploaded_at": document.uploaded_at.isoformat(),
        }
    ), 201


def _can_view_documents(user_role, user_commune_id, declaration):
    """Enforce access control for document viewing."""
    if user_role in [UserRole.MINISTRY_ADMIN.value]:
        return False
    if user_role in [UserRole.CITIZEN.value, UserRole.BUSINESS.value]:
        return declaration.owner_id == get_current_user_id()
    if user_role in [
        UserRole.MUNICIPAL_ADMIN.value,
        UserRole.MUNICIPAL_AGENT.value,
        UserRole.INSPECTOR.value,
        UserRole.FINANCE_OFFICER.value,
        UserRole.CONTENTIEUX_OFFICER.value,
        UserRole.URBANISM_OFFICER.value,
    ]:
        return user_commune_id and user_commune_id == declaration.commune_id
    return False


@blp.get("/declarations/<int:declaration_id>/documents")
@blp.response(200)
@jwt_required()
def list_documents(declaration_id):
    """List documents for a declaration with role-based filtering."""

    declaration = Declaration.query.get(declaration_id)
    if not declaration:
        return jsonify({"error": "Declaration not found"}), 404

    user_commune_id, user_role = _get_commune_and_role()
    if not _can_view_documents(user_role, user_commune_id, declaration):
        return jsonify({"error": "Access denied"}), 403

    docs = (
        Document.query.filter_by(declaration_id=declaration_id, is_deleted=False)
        .order_by(Document.uploaded_at.desc())
        .all()
    )

    return jsonify(
        {
            "documents": [
                {
                    "id": d.id,
                    "type": d.document_type.code,
                    "label": d.document_type.label,
                    "status": d.status.value,
                    "version": d.version,
                    "issue_date": d.issue_date.isoformat() if d.issue_date else None,
                    "uploaded_at": d.uploaded_at.isoformat() if d.uploaded_at else None,
                    "reviewed_by": d.reviewed_by,
                    "review_date": d.review_date.isoformat() if d.review_date else None,
                    "review_comment": d.review_comment,
                }
                for d in docs
            ]
        }
    ), 200


@blp.put("/documents/<int:document_id>/review")
@blp.arguments(DocumentReviewSchema, location="json")
@blp.response(200)
@jwt_required()
@role_required(UserRole.URBANISM_OFFICER, UserRole.INSPECTOR)
def review_document(data, document_id):
    """Review a document (urbanism officer or inspector)."""

    reviewer_id = get_current_user_id()
    claims = get_jwt()
    user_commune_id = claims.get("commune_id")

    data = request.get_json() or {}
    status = data.get("status")
    comment = data.get("comment")

    if status not in [s.value for s in DocumentStatus]:
        return jsonify({"error": "Invalid status"}), 400

    document = Document.query.get(document_id)
    if not document or document.is_deleted:
        return jsonify({"error": "Document not found"}), 404

    if document.status != DocumentStatus.PENDING:
        return jsonify({"error": "Only PENDING documents can be reviewed"}), 400

    declaration = document.declaration
    if not user_commune_id or declaration.commune_id != user_commune_id:
        return jsonify({"error": "Access denied"}), 403

    document.status = DocumentStatus(status)
    document.review_comment = comment
    document.reviewed_by = reviewer_id
    document.review_date = datetime.utcnow()

    db.session.commit()

    return jsonify(
        {
            "message": "Document reviewed",
            "document_id": document.id,
            "status": document.status.value,
            "reviewed_by": reviewer_id,
            "review_date": document.review_date.isoformat(),
        }
    ), 200


@blp.get("/documents/<int:document_id>/file")
@blp.response(200)
@jwt_required()
def download_document(document_id):
    """Secure download endpoint with role-based access and soft-delete guard."""

    document = Document.query.get(document_id)
    if not document or document.is_deleted:
        return jsonify({"error": "Document not found"}), 404

    declaration = document.declaration
    if not declaration:
        return jsonify({"error": "Invalid declaration"}), 400

    user_commune_id, user_role = _get_commune_and_role()
    if not _can_view_documents(user_role, user_commune_id, declaration):
        return jsonify({"error": "Access denied"}), 403

    if not os.path.exists(document.storage_path):
        return jsonify({"error": "File missing from storage"}), 404

    return send_file(
        document.storage_path,
        mimetype=document.mime_type,
        as_attachment=True,
        download_name=document.file_name,
        max_age=0,
    )

