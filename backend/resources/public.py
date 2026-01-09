"""Public API routes (no auth required)"""
from flask import jsonify, request
from flask_smorest import Blueprint
import yaml
import os
import json
import csv
from pathlib import Path
from models import Commune, DocumentRequirement

blp = Blueprint('public', 'public', url_prefix='/api/v1/public')

@blp.get('/tax-rates')
def get_tax_rates():
    """Get current tax tariff rates
    
    Returns the 2025 tax tariff rates for TIB and TTNB calculations.
    No authentication required.
    
    Returns:
        200: Tax rates by type
        500: Tariff rates not available
    """
    yaml_path = os.path.join(os.path.dirname(__file__), 'tariffs_2025.yaml')
    
    try:
        with open(yaml_path, 'r', encoding='utf-8') as f:
            tariffs = yaml.safe_load(f)
    except:
        return jsonify({'error': 'Tariff rates not available'}), 500
    
    return jsonify({
        'year': 2025,
        'tariffs': tariffs
    }), 200

@blp.post('/calculator')
def estimate_tax():
    """Public tax calculator - estimate before declaring
    
    Provides tax estimates for TIB (property tax) or TTNB (land tax) before official declaration.
    
    Request body:
        - tax_type: "tib" or "ttnb" (required)
        - For TIB: surface_couverte, reference_price (optional: service_rate, is_exempt)
        - For TTNB: surface, land_type (optional: is_exempt)
    
    Returns:
        200: Estimated tax calculation
        400: Invalid tax type or missing fields
    """
    data = request.get_json()
    
    if not data.get('tax_type'):
        return jsonify({'error': 'tax_type required (tib or ttnb)'}), 400
    
    from utils.calculator import TaxCalculator
    
    try:
        if data['tax_type'] == 'tib':
            # Create mock property object that mirrors real Property fields
            class MockProperty:
                def __init__(self, d):
                    self.surface_couverte = d.get('surface_couverte', 100)
                    self.reference_price_per_m2 = (
                        d.get('reference_price_per_m2') or d.get('reference_price')
                    )
                    self.commune_id = d.get('commune_id')
                    self.delegation = d.get('delegation')
                    self.is_exempt = d.get('is_exempt', False)
                    self.exemption_reason = d.get('exemption_reason')
            
            mock_prop = MockProperty(data)
            result = TaxCalculator.calculate_tib(mock_prop)
        else:
            # Create mock land object
            class MockLand:
                def __init__(self, d):
                    self.surface = d.get('surface', 1000)
                    self.urban_zone = d.get('urban_zone')
                    self.is_exempt = d.get('is_exempt', False)
                    self.exemption_reason = d.get('exemption_reason')
            
            mock_land = MockLand(data)
            result = TaxCalculator.calculate_ttnb(mock_land)
        
        if 'error' in result:
            return jsonify({'error': result['error']}), 400
        
        return jsonify({
            'estimate': result,
            'disclaimer': 'This is an estimate. Actual tax may vary based on verification.'
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@blp.get('/communes')
def list_communes():
    """List available communes (municipalities) with optional search.
    Query params: search (substring on name or code)
    """
    q = (request.args.get('search') or '').strip().lower()
    query = Commune.query
    if q:
        # Simple LIKE filter on name or exact code
        like = f"%{q}%"
        query = query.filter(
            (Commune.nom_municipalite_fr.ilike(like)) | (Commune.code_municipalite.ilike(like))
        )
    communes = query.order_by(Commune.nom_municipalite_fr.asc()).all()
    return jsonify({
        'communes': [
            {
                'id': c.id,
                'code': c.code_municipalite,
                'name': c.nom_municipalite_fr,
                'governorate_code': c.code_gouvernorat,
                'governorate_name': c.nom_gouvernorat_fr,
                'type': c.type_mun_fr,
            }
            for c in communes
        ]
    }), 200


def _resolve_localities_csv():
    """Locate the CSV file regardless of whether it's under backend/data or repo-root/data."""
    this_file = Path(__file__).resolve()
    candidates = [
        this_file.parent / 'data' / 'localities.csv',  # legacy location (unused but kept)
        this_file.parent.parent / 'data' / 'codes.csv',  # backend/data/codes.csv
        this_file.parents[2] / 'data' / 'codes.csv',  # repo-root/data/codes.csv
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


@blp.get('/localities')
def list_localities():
    """Return localities list for a given commune (by id or code), sourced from CSV.
    Query params: commune_id or commune_code, optional delegation, optional search
    The data source is data/codes.csv with columns: Governorate, Delegation, Locality, postal code
    """
    commune_id = request.args.get('commune_id')
    commune_code = request.args.get('commune_code')
    delegation_param = (request.args.get('delegation') or '').strip()
    delegation_filter = delegation_param.lower()
    search = (request.args.get('search') or '').strip().lower()

    # Resolve commune and governorate
    gov_name = None
    deleg_name = None
    if commune_code or commune_id:
        try:
            c = None
            if commune_id:
                c = Commune.query.get(int(commune_id))
            if not c and commune_code:
                c = Commune.query.filter_by(code_municipalite=commune_code).first()
            if c:
                commune_code = c.code_municipalite
                gov_name = (c.nom_gouvernorat_fr or '').strip().upper()
                # Use commune name as delegation (commune name = delegation name in CSV)
                deleg_name = (c.nom_municipalite_fr or '').strip().upper()
        except Exception:
            pass

    # Load CSV of localities
    csv_path = _resolve_localities_csv()
    items = []
    if csv_path and os.path.exists(csv_path):
        try:
            with open(csv_path, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                header = next(reader, None)
                for row in reader:
                    if len(row) < 4:
                        continue
                    gov, deleg, loc, postal = row[0].strip().upper(), row[1].strip(), row[2].strip(), row[3].strip()
                    # Filter by governorate first
                    if gov_name and gov != gov_name:
                        continue
                    if search and (search not in loc.lower() and search not in deleg.lower()):
                        continue
                    items.append({'delegation': deleg, 'locality': loc, 'postal_code': postal})
        except Exception:
            items = []

    # Apply delegation filter after loading so we can gracefully fall back if it doesn't match anything.
    if items and delegation_filter:
        exact_matches = [it for it in items if it['delegation'].lower() == delegation_filter]
        if exact_matches:
            items = exact_matches
        else:
            partial_matches = [it for it in items if delegation_filter in it['delegation'].lower()]
            if partial_matches:
                items = partial_matches
            # If no match at all, keep the full governorate list rather than returning empty

    # Deduplicate localities by name while preserving delegation info
    seen = set()
    unique_localities = []
    for it in items:
        key = (it['locality'].lower(), it['delegation'].lower())
        if key in seen:
            continue
        seen.add(key)
        unique_localities.append(it)

    # Return only locality names (and delegation for context)
    return jsonify({
        'commune_code': commune_code,
        'governorate': gov_name,
        'delegation': deleg_name,
        'localities': [
            {
                'name': it['locality'],
                'delegation': it['delegation'],
                'postal_code': it['postal_code']
            } for it in unique_localities
        ]
    }), 200


@blp.get('/localities')
def list_delegations():
    """Return delegations for a commune's governorate (or by governorate name)."""
    commune_id = request.args.get('commune_id')
    commune_code = request.args.get('commune_code')
    governorate_param = (request.args.get('governorate') or '').strip()
    search = (request.args.get('search') or '').strip().lower()

    gov_name = None
    if commune_code or commune_id:
        try:
            c = None
            if commune_id:
                c = Commune.query.get(int(commune_id))
            if not c and commune_code:
                c = Commune.query.filter_by(code_municipalite=commune_code).first()
            if c:
                gov_name = (c.nom_gouvernorat_fr or '').strip().upper()
        except Exception:
            pass
    if not gov_name and governorate_param:
        gov_name = governorate_param.strip().upper()

    csv_path = _resolve_localities_csv()
    delegations = []
    if csv_path and os.path.exists(csv_path):
        try:
            with open(csv_path, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                header = next(reader, None)
                seen = set()
                for row in reader:
                    if len(row) < 2:
                        continue
                    gov, deleg = row[0].strip().upper(), row[1].strip()
                    if gov_name and gov != gov_name:
                        continue
                    if search and search not in deleg.lower():
                        continue
                    key = deleg.lower()
                    if key in seen:
                        continue
                    seen.add(key)
                    delegations.append({'name': deleg, 'governorate': gov})
        except Exception:
            delegations = []

    delegations = sorted(delegations, key=lambda d: d['name'])
    return jsonify({
        'governorate': gov_name,
        'delegations': delegations
    }), 200


@blp.get('/document-requirements')
def get_document_requirements():
    """Get required documents for a declaration type and commune.
    
    Query parameters:
        - declaration_type: "property" or "land" (required)
        - commune_id: ID of the commune (required)
        - include_optional: "true" to include optional documents, default "false" (optional)
    
    Returns:
        200: List of required documents
        400: Missing required parameters
        404: Commune or document requirements not found
    """
    declaration_type = request.args.get('declaration_type')
    commune_id = request.args.get('commune_id')
    include_optional = request.args.get('include_optional', 'false').lower() == 'true'
    
    if not declaration_type or not commune_id:
        return jsonify({'error': 'declaration_type and commune_id required'}), 400
    
    if declaration_type not in ['property', 'land']:
        return jsonify({'error': 'declaration_type must be property or land'}), 400
    
    try:
        commune_id = int(commune_id)
    except ValueError:
        return jsonify({'error': 'commune_id must be an integer'}), 400
    
    # Verify commune exists
    commune = Commune.query.get(commune_id)
    if not commune:
        return jsonify({'error': 'Commune not found'}), 404
    
    # Get requirements for this type and commune
    # Include both specific type and "all" types
    requirements = DocumentRequirement.query.filter(
        (DocumentRequirement.commune_id == commune_id) &
        ((DocumentRequirement.declaration_type == declaration_type) |
         (DocumentRequirement.declaration_type == 'all'))
    ).order_by(DocumentRequirement.display_order).all()
    
    # Filter by mandatory if not including optional
    if not include_optional:
        requirements = [r for r in requirements if r.is_mandatory]
    
    return jsonify({
        'commune_id': commune_id,
        'commune_name': commune.nom_municipalite_fr,
        'declaration_type': declaration_type,
        'total_documents': len(requirements),
        'documents': [{
            'id': r.id,
            'document_code': r.document_code,
            'document_name': r.document_name,
            'description': r.description,
            'is_mandatory': r.is_mandatory
        } for r in requirements]
    }), 200
