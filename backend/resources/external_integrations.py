"""External API integration endpoints (Nominatim + NASA).

SECURITY: All endpoints require JWT authentication (via Bearer token in Authorization header).
This prevents unauthorized API usage and helps track which users are consuming external APIs.

RATE LIMITING:
- Nominatim endpoints: 10 requests/minute per user
- NASA endpoints: 5 requests/minute per user
- Currently uses in-memory (fixed-window) rate limiting via Flask-Limiter
- NOT persistent across process restarts; each worker process maintains its own limit state

PRODUCTION RECOMMENDATIONS:
1. Redis-backed rate limiting (distributed across workers)
   - Configure: RATELIMIT_STORAGE_URL=redis://localhost:6379
   
2. API key layer (if exposing publicly):
   - Require API keys for higher rate limits
   - Track usage per key, charge overage fees
   
3. Request signing/HMAC validation:
   - Prevent request spoofing, add integrity checks
   
4. Caching strategy:
   - SimpleTTLCache is in-memory only (5-min default)
   - Switch to Redis cache for multi-worker deployments
   - Consider full response caching for read-only endpoints
"""
from flask import jsonify, request
from flask_jwt_extended import jwt_required
from flask_smorest import Blueprint

from extensions.limiter import limiter
from extensions.db import db
from models import SatelliteVerification
from utils.external_apis import ExternalAPIError, NasaClient, NominatimClient

blp = Blueprint("external_integrations", "external_integrations", url_prefix="/api/v1/external")

# Shared clients with lightweight caching to respect free API limits
_nominatim = NominatimClient()
_nasa = NasaClient()


@blp.get("/geocode")
@jwt_required()
@limiter.limit("10/minute")
def geocode_address():
    """Geocode a free-form address using Nominatim (OpenStreetMap)."""
    query = (request.args.get("q") or request.args.get("address") or "").strip()
    limit = max(1, min(int(request.args.get("limit", 1)), 5))
    if not query:
        return jsonify({"error": "Query parameter 'q' or 'address' is required"}), 400

    try:
        result = _nominatim.geocode(query=query, limit=limit)
        return jsonify(result), 200
    except ExternalAPIError as exc:
        return jsonify({
            "error": "Geocoding service unavailable",
            "details": exc.message,
            "source": exc.source,
            "status_code": exc.status_code,
        }), 502
    except Exception:
        return jsonify({"error": "Unexpected geocoding failure"}), 502


@jwt_required()
@blp.get("/reverse-geocode")
@limiter.limit("10/minute")
def reverse_geocode():
    """Reverse geocode latitude/longitude into a human-readable address."""
    try:
        lat = float(request.args.get("lat"))
        lon = float(request.args.get("lon"))
    except (TypeError, ValueError):
        return jsonify({"error": "Valid 'lat' and 'lon' query parameters are required"}), 400

    try:
        result = _nominatim.reverse(latitude=lat, longitude=lon)
        return jsonify(result), 200
    except ExternalAPIError as exc:
        return jsonify({
            "error": "Reverse geocoding service unavailable",
            "details": exc.message,
            "source": exc.source,
            "status_code": exc.status_code,
        }), 502
    except Exception:
        return jsonify({"error": "Unexpected reverse geocoding failure"}), 502


@jwt_required()
@blp.get("/nasa/imagery")
@limiter.limit("5/minute")
def nasa_imagery_search():
    """Search NASA Images API for earth observation media."""
    query = (request.args.get("q") or "Tunisia earth").strip()
    page = max(1, min(int(request.args.get("page", 1)), 10))
    page_size = max(1, min(int(request.args.get("page_size", 5)), 20))
    media_type = request.args.get("media_type", "image")

    try:
        result = _nasa.search_imagery(query=query, media_type=media_type, page=page, page_size=page_size)
        return jsonify(result), 200
    except ExternalAPIError as exc:
        return jsonify({
            "error": "NASA imagery service unavailable",
            "details": exc.message,
            "source": exc.source,
            "status_code": exc.status_code,
        }), 502
    except Exception:
        return jsonify({"error": "Unexpected NASA imagery failure"}), 502


@jwt_required()
@blp.get("/nasa/events")
@jwt_required()
@limiter.limit("5/minute")
def nasa_events():
    """List recent Earth events (EONET)."""
    try:
        limit = max(1, min(int(request.args.get("limit", 5)), 20))
    except (TypeError, ValueError):
        return jsonify({"error": "Limit must be an integer"}), 400

    try:
        result = _nasa.list_events(limit=limit)
        return jsonify(result), 200
    except ExternalAPIError as exc:
        return jsonify({
            "error": "NASA EONET service unavailable",
            "details": exc.message,
            "source": exc.source,
            "status_code": exc.status_code,
        }), 502
    except Exception:
        return jsonify({"error": "Unexpected NASA events failure"}), 502


# Satellite verification is now persisted to the database via SatelliteVerification model

@blp.post("/inspector/satellite-verification")
@jwt_required()
def record_satellite_verification():
    """Record satellite imagery verification findings.
    
    This endpoint stores verification records indicating whether satellite imagery
    is accurate, outdated, or shows discrepancies vs. field inspection findings.
    """
    from flask_jwt_extended import get_jwt_identity
    from datetime import datetime
    import uuid
    
    inspector_id = get_jwt_identity()
    data = request.get_json() or {}
    
    # Validate required fields
    status = data.get('verification_status', '').strip()
    valid_statuses = ['verified_accurate', 'verified_needs_update', 'discrepancy_found', 'unclear_inconclusive']
    if status not in valid_statuses:
        return jsonify({"error": f"Invalid status. Must be one of: {', '.join(valid_statuses)}"}), 400
    
    # Create DB record
    record_id = str(uuid.uuid4())
    verified_at = None
    if data.get('verified_at'):
        try:
            verified_at = datetime.fromisoformat(data.get('verified_at'))
        except Exception:
            verified_at = datetime.utcnow()

    sv = SatelliteVerification(
        id=record_id,
        inspector_id=int(inspector_id),
        property_id=data.get('property_id'),
        land_id=data.get('land_id'),
        satellite_image_url=data.get('satellite_image_url'),
        image_source=data.get('image_source', 'nasa'),
        verification_status=status,
        discrepancy_severity=data.get('discrepancy_severity'),
        discrepancy_notes=data.get('discrepancy_notes', ''),
        has_photo_evidence=bool(data.get('has_photo_evidence')),
        verified_at=verified_at,
    )

    db.session.add(sv)
    db.session.commit()

    return jsonify({
        "id": record_id,
        "message": "Satellite verification recorded successfully",
        "status": status,
        "timestamp": sv.created_at.isoformat()
    }), 201
