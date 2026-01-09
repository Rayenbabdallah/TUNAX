"""Search and Filter routes"""
from flask import jsonify, request
from flask_smorest import Blueprint
from flask_jwt_extended import jwt_required
from utils.jwt_helpers import get_current_user_id
from models.property import Property, PropertyAffectation
from models.land import Land, LandType
from utils.role_required import citizen_or_business_required

blp = Blueprint('search', 'search', url_prefix='/api/v1/search')

@blp.get('/properties')
@blp.response(200)
@jwt_required()
def search_properties():
    """Search and filter properties with advanced criteria
    
    Search for properties using multiple filter criteria including location, surface area,
    construction year, usage type, and exemption status. Results are paginated.
    
    ---
    parameters:
      - name: city
        in: query
        type: string
        description: Filter by city name (partial match, case-insensitive)
      - name: affectation
        in: query
        type: string
        enum: [residential, commercial, industrial, mixed]
        description: Filter by property usage type
      - name: surface_min
        in: query
        type: number
        format: float
        description: Minimum covered surface area in m²
      - name: surface_max
        in: query
        type: number
        format: float
        description: Maximum covered surface area in m²
      - name: construction_year_min
        in: query
        type: integer
        description: Minimum construction year
      - name: construction_year_max
        in: query
        type: integer
        description: Maximum construction year
      - name: is_exempt
        in: query
        type: boolean
        description: Filter by exemption status (true/false)
      - name: page
        in: query
        type: integer
        default: 1
        description: Page number for pagination
      - name: per_page
        in: query
        type: integer
        default: 20
        description: Number of results per page
    responses:
      200:
        description: Paginated search results
        schema:
          type: object
          properties:
            total:
              type: integer
              description: Total number of matching properties
            page:
              type: integer
              description: Current page number
            per_page:
              type: integer
              description: Results per page
            pages:
              type: integer
              description: Total number of pages
            properties:
              type: array
              items:
                type: object
                properties:
                  id:
                    type: integer
                  street_address:
                    type: string
                  city:
                    type: string
                  surface_couverte:
                    type: number
                  construction_year:
                    type: integer
                  affectation:
                    type: string
                  is_exempt:
                    type: boolean
    """
    # Get query parameters
    city = request.args.get('city')
    affectation = request.args.get('affectation')
    surface_min = request.args.get('surface_min', type=float)
    surface_max = request.args.get('surface_max', type=float)
    construction_year_min = request.args.get('construction_year_min', type=int)
    construction_year_max = request.args.get('construction_year_max', type=int)
    is_exempt = request.args.get('is_exempt', type=bool)
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    
    query = Property.query
    
    if city:
        query = query.filter(Property.city.ilike(f'%{city}%'))
    if affectation:
        # Convert string to enum
        try:
            affectation_enum = PropertyAffectation(affectation.lower())
            query = query.filter_by(affectation=affectation_enum)
        except ValueError:
            return jsonify({'error': f'Invalid affectation value: {affectation}'}), 400
    if surface_min is not None:
        query = query.filter(Property.surface_couverte >= surface_min)
    if surface_max is not None:
        query = query.filter(Property.surface_couverte <= surface_max)
    if construction_year_min is not None:
        query = query.filter(Property.construction_year >= construction_year_min)
    if construction_year_max is not None:
        query = query.filter(Property.construction_year <= construction_year_max)
    if is_exempt is not None:
        query = query.filter_by(is_exempt=is_exempt)
    
    try:
        results = query.paginate(page=page, per_page=per_page, error_out=False)
        
        return jsonify({
            'total': results.total,
            'page': page,
            'per_page': per_page,
            'pages': results.pages,
            'properties': [{
                'id': p.id,
                'city': p.city,
                'street_address': p.street_address,
                'surface_couverte': p.surface_couverte,
                'affectation': p.affectation.value if hasattr(p.affectation, 'value') else p.affectation,
                'construction_year': p.construction_year,
                'reference_price': p.reference_price_per_m2
            } for p in results.items]
        }), 200
    except Exception as e:
        return jsonify({'error': 'Search failed', 'message': str(e)}), 500

@blp.get('/lands')
@blp.response(200)
@jwt_required()
def search_lands():
    """Search and filter land parcels with advanced criteria
    
    Search for land parcels using multiple filter criteria including location, surface area,
    land type, and exemption status. Results are paginated.
    
    ---
    parameters:
      - name: city
        in: query
        type: string
        description: Filter by city name (partial match, case-insensitive)
      - name: land_type
        in: query
        type: string
        enum: [agricultural, residential, commercial, industrial]
        description: Filter by land type/usage
      - name: surface_min
        in: query
        type: number
        format: float
        description: Minimum surface area in m²
      - name: surface_max
        in: query
        type: number
        format: float
        description: Maximum surface area in m²
      - name: is_exempt
        in: query
        type: boolean
        description: Filter by exemption status (true/false)
      - name: page
        in: query
        type: integer
        default: 1
        description: Page number for pagination
      - name: per_page
        in: query
        type: integer
        default: 20
        description: Number of results per page
    responses:
      200:
        description: Paginated search results for land parcels
        schema:
          type: object
          properties:
            total:
              type: integer
              description: Total number of matching land parcels
            page:
              type: integer
              description: Current page number
            per_page:
              type: integer
              description: Results per page
            pages:
              type: integer
              description: Total number of pages
            lands:
              type: array
              items:
                type: object
                properties:
                  id:
                    type: integer
                  street_address:
                    type: string
                  city:
                    type: string
                  surface:
                    type: number
                    description: Surface area in m²
                  land_type:
                    type: string
                  vénale_value:
                    type: number
                    description: Market value
                  is_exempt:
                    type: boolean
    """
    # Get query parameters
    city = request.args.get('city')
    land_type = request.args.get('land_type')
    surface_min = request.args.get('surface_min', type=float)
    surface_max = request.args.get('surface_max', type=float)
    is_exempt = request.args.get('is_exempt', type=bool)
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    
    query = Land.query
    
    if city:
        query = query.filter(Land.city.ilike(f'%{city}%'))
    if land_type:
        # Convert string to enum
        try:
            land_type_enum = LandType(land_type.lower())
            query = query.filter_by(land_type=land_type_enum)
        except ValueError:
            return jsonify({'error': f'Invalid land_type value: {land_type}'}), 400
    if surface_min is not None:
        query = query.filter(Land.surface >= surface_min)
    if surface_max is not None:
        query = query.filter(Land.surface <= surface_max)
    if is_exempt is not None:
        query = query.filter_by(is_exempt=is_exempt)
    
    try:
        results = query.paginate(page=page, per_page=per_page, error_out=False)
        
        # Debug: print the first land to see what's happening
        import traceback
        lands_list = []
        for l in results.items:
            try:
                land_dict = {
                    'id': l.id,
                    'city': l.city,
                    'street_address': l.street_address,
                    'surface': l.surface,
                    'land_type': l.land_type.value if hasattr(l.land_type, 'value') else l.land_type,
                    'urban_zone': l.urban_zone
                }
                lands_list.append(land_dict)
            except AttributeError as ae:
                import sys
                traceback.print_exc()
                raise
        
        return jsonify({
            'total': results.total,
            'page': page,
            'per_page': per_page,
            'pages': results.pages,
            'lands': lands_list
        }), 200
    except Exception as e:
        import traceback
        log_path = r'C:\Users\rayen\Desktop\TUNAX\search_error.log'
        with open(log_path, 'a') as f:
            f.write(f"\n=== ERROR at {__import__('datetime').datetime.now()} ===\n")
            f.write(traceback.format_exc())
        return jsonify({'error': 'Search failed', 'message': str(e)}), 500
