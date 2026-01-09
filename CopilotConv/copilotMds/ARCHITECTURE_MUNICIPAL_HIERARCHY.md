# TUNAX Architecture Redesign - Municipal Hierarchy & Reference Prices

**Date**: December 14, 2025  
**Status**: Architecture Design Document

---

## 1. CURRENT PROBLEM & NEW REQUIREMENTS

### Current (WRONG):
- Single global admin with all privileges
- Global/uniform reference prices for all municipalities
- Service counts uniform nationwide
- No municipality isolation
- No data segregation

### NEW (CORRECT):
- **Two-tier admin system**: Ministry Admin (super) + Municipal Admins (per commune)
- **Municipality-specific reference prices**: Each commune sets its own TIB reference price ranges
- **Municipality-specific service counts**: Each commune defines which services are available
- **Data isolation**: Users/agents/officers only access their commune's data
- **Multi-tenancy**: System operates as municipality-scoped microservices

---

## 2. NEW USER ROLE HIERARCHY

### 2.1 Ministry Level (Nation-wide)

**Role: MINISTRY_ADMIN** (new)
- Super admin for entire Tunisia
- Creates municipal administrations
- Views nation-wide reports & statistics
- Can override/audit any municipality
- Manages system configuration

**Endpoints**: `/api/ministry/...`

### 2.2 Municipal Level (Per Commune)

Each municipality (from communes_tn.csv) has:

| Role | Responsibility | Scope |
|------|-----------------|-------|
| **MUNICIPAL_ADMIN** | Sets policies, reference prices, service configs | Own municipality only |
| **MUNICIPAL_AGENT** | Verifies declarations, validates data | Own municipality only |
| **INSPECTOR** | Field inspections, satellite verification | Own municipality only |
| **FINANCE_OFFICER** | Tax recovery, payment attestations | Own municipality only |
| **CONTENTIEUX_OFFICER** | Dispute resolution, commissions | Own municipality only |
| **URBANISM_OFFICER** | Permits, building validation | Own municipality only |

### 2.3 User Level (Citizens/Businesses)

| Role | Behavior |
|------|----------|
| **CITIZEN** | Declares property/land in their municipality |
| **BUSINESS** | Declares business/commercial in their municipality |

---

## 3. NEW DATA MODELS

### 3.1 Commune Model

```python
class Commune(db.Model):
    """Municipality entity from communes_tn.csv"""
    id = db.Column(db.Integer, primary_key=True)
    code_municipalite = db.Column(db.String(10), unique=True)  # e.g., "1111"
    nom_municipalite_fr = db.Column(db.String(255))  # e.g., "Tunis Ville"
    code_gouvernorat = db.Column(db.String(10))  # e.g., "11"
    nom_gouvernorat_fr = db.Column(db.String(255))  # e.g., "Tunis"
    type_mun_fr = db.Column(db.String(50))  # "Ancienne", "Extension", "Nouvelle"
    
    # Relationships
    reference_prices = db.relationship('MunicipalReferencePrice', back_populates='commune')
    service_configs = db.relationship('MunicipalServiceConfig', back_populates='commune')
    users = db.relationship('User', back_populates='commune')
    properties = db.relationship('Property', back_populates='commune')
    lands = db.relationship('Land', back_populates='commune')
```

### 3.2 MunicipalReferencePrice Model

```python
class MunicipalReferencePrice(db.Model):
    """TIB reference prices set by municipal admin per category"""
    id = db.Column(db.Integer, primary_key=True)
    commune_id = db.Column(db.Integer, db.ForeignKey('commune.id'), nullable=False)
    
    # TIB Category (1-4)
    tib_category = db.Column(db.Integer)  # 1, 2, 3, or 4
    
    # Legal bounds from law
    legal_min = db.Column(db.Float)  # e.g., 100 for Cat 1
    legal_max = db.Column(db.Float)  # e.g., 178 for Cat 1
    
    # Municipality's chosen reference price (MUST be within bounds)
    reference_price_per_m2 = db.Column(db.Float)
    
    # Audit
    set_by_user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    set_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    commune = db.relationship('Commune', back_populates='reference_prices')
    set_by_user = db.relationship('User', foreign_keys=[set_by_user_id])
    
    __table_args__ = (
        db.UniqueConstraint('commune_id', 'tib_category', name='unique_ref_price_per_commune_category'),
    )
```

### 3.3 MunicipalServiceConfig Model

```python
class MunicipalServiceConfig(db.Model):
    """Services available in each municipality"""
    id = db.Column(db.Integer, primary_key=True)
    commune_id = db.Column(db.Integer, db.ForeignKey('commune.id'), nullable=False)
    
    # Service definition
    service_name = db.Column(db.String(255))  # e.g., "Water", "Electricity", "Sewage"
    service_code = db.Column(db.String(50))  # e.g., "water", "electricity"
    
    # Availability flag
    is_available = db.Column(db.Boolean, default=True)
    
    # Audit
    configured_by_user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    configured_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    commune = db.relationship('Commune', back_populates='service_configs')
    configured_by_user = db.relationship('User', foreign_keys=[configured_by_user_id])
    
    __table_args__ = (
        db.UniqueConstraint('commune_id', 'service_code', name='unique_service_per_commune'),
    )
```

### 3.4 Modified User Model

```python
class User(db.Model):
    """Updated with municipality association"""
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(255), unique=True, nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password_hash = db.Column(db.String(255))
    role = db.Column(db.Enum(UserRole), nullable=False)
    
    # NEW: Municipality association
    commune_id = db.Column(db.Integer, db.ForeignKey('commune.id'))
    
    # Audit
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    commune = db.relationship('Commune', back_populates='users')
    
    # Validation
    @validates('role', 'commune_id')
    def validate_role_commune(self, key, value):
        if key == 'role':
            if value in [UserRole.CITIZEN, UserRole.BUSINESS]:
                # Citizens/businesses can register without approval
                return value
            elif value in [UserRole.MINISTRY_ADMIN]:
                # Only ONE ministry admin (check elsewhere)
                return value
            elif value in [UserRole.MUNICIPAL_ADMIN, UserRole.MUNICIPAL_AGENT,
                          UserRole.INSPECTOR, UserRole.FINANCE_OFFICER,
                          UserRole.CONTENTIEUX_OFFICER, UserRole.URBANISM_OFFICER]:
                # Must have commune_id
                if not self.commune_id:
                    raise ValueError(f"Role {value} requires commune_id")
                return value
        return value
```

### 3.5 Modified Property & Land Models

```python
class Property(db.Model):
    """Updated with commune association"""
    id = db.Column(db.Integer, primary_key=True)
    owner_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # NEW: Municipality reference
    commune_id = db.Column(db.Integer, db.ForeignKey('commune.id'), nullable=False)
    
    # Property details
    street_address = db.Column(db.String(500))
    city = db.Column(db.String(255))
    delegation = db.Column(db.String(255))
    post_code = db.Column(db.String(10))
    
    # TIB specifics
    surface_couverte = db.Column(db.Float)
    surface_totale = db.Column(db.Float)
    affectation = db.Column(db.String(50))
    nb_floors = db.Column(db.Integer)
    nb_rooms = db.Column(db.Integer)
    construction_year = db.Column(db.Integer)
    
    # NEW: Reference price (per m²) for THIS municipality
    reference_price_per_m2 = db.Column(db.Float)
    
    # Relationships
    commune = db.relationship('Commune', back_populates='properties')
    owner = db.relationship('User', foreign_keys=[owner_id])
    taxes = db.relationship('Tax', back_populates='property')
    
    __table_args__ = (
        db.ForeignKeyConstraint(['commune_id'], ['commune.id']),
        db.UniqueConstraint('owner_id', 'street_address', 'city', 'commune_id', 
                           name='unique_property_per_owner_commune'),
    )

class Land(db.Model):
    """Updated with commune and zone classification"""
    id = db.Column(db.Integer, primary_key=True)
    owner_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # NEW: Municipality reference
    commune_id = db.Column(db.Integer, db.ForeignKey('commune.id'), nullable=False)
    
    # Land details
    street_address = db.Column(db.String(500))
    city = db.Column(db.String(255))
    delegation = db.Column(db.String(255))
    post_code = db.Column(db.String(10))
    surface = db.Column(db.Float)
    
    # NEW: Urban zone classification (REQUIRED for TTNB)
    # Values: "haute_densite", "densite_moyenne", "faible_densite", "peripherique"
    urban_zone = db.Column(db.String(50))  # MUST BE SET
    
    # Relationships
    commune = db.relationship('Commune', back_populates='lands')
    owner = db.relationship('User', foreign_keys=[owner_id])
    taxes = db.relationship('Tax', back_populates='land')
    
    __table_args__ = (
        db.ForeignKeyConstraint(['commune_id'], ['commune.id']),
        db.UniqueConstraint('owner_id', 'street_address', 'city', 'commune_id',
                           name='unique_land_per_owner_commune'),
    )
```

---

## 4. NEW UPDATED USER ROLES ENUM

```python
class UserRole(str, Enum):
    """User roles with two-tier hierarchy"""
    
    # Ministry level (nation-wide)
    MINISTRY_ADMIN = 'ministry_admin'
    
    # Municipal level (per commune)
    MUNICIPAL_ADMIN = 'municipal_admin'
    MUNICIPAL_AGENT = 'municipal_agent'
    INSPECTOR = 'inspector'
    FINANCE_OFFICER = 'finance_officer'
    CONTENTIEUX_OFFICER = 'contentieux_officer'
    URBANISM_OFFICER = 'urbanism_officer'
    
    # User level (citizens/businesses)
    CITIZEN = 'citizen'
    BUSINESS = 'business'
```

---

## 5. NEW ENDPOINTS - MINISTRY ADMIN

### Ministry Admin Dashboard

```
GET /api/ministry/dashboard
  → Nation-wide statistics (total properties, taxes, disputes)
  → Revenue by municipality
  → Performance metrics per municipality
```

### Manage Municipalities

```
GET /api/ministry/municipalities
  → List all communes with their admins

GET /api/ministry/municipalities/<commune_id>
  → Detailed info for one municipality
  
PATCH /api/ministry/municipalities/<commune_id>
  → Update municipal settings
```

### Manage Municipal Admins

```
POST /api/ministry/municipal-admins
  → Create municipal admin for a commune
  → Body: { "username", "email", "password", "commune_id" }

GET /api/ministry/municipal-admins
  → List all municipal admins by commune

PATCH /api/ministry/municipal-admins/<user_id>
  → Enable/disable/reassign municipal admin

DELETE /api/ministry/municipal-admins/<user_id>
  → Remove municipal admin
```

### Audit & Reports

```
GET /api/ministry/audit-log
  → All administrative actions (who set what, when)

GET /api/ministry/reports/reference-prices
  → All reference prices by municipality

GET /api/ministry/reports/revenue
  → Total revenue by municipality
```

---

## 6. NEW ENDPOINTS - MUNICIPAL ADMIN

### Set Reference Prices (TIB)

```
PUT /api/municipal/reference-prices/<category>
  → Set reference price for TIB category (1-4)
  → Body: { "reference_price_per_m2": 150 }
  → Validation: Must be within legal bounds for category
  → Only municipal admin can do this for their commune
  
GET /api/municipal/reference-prices
  → View current reference prices for all categories
```

### Configure Services

```
GET /api/municipal/services
  → List all available services in municipality
  
POST /api/municipal/services
  → Add/enable service
  → Body: { "service_name": "Water", "service_code": "water" }

PATCH /api/municipal/services/<service_id>
  → Enable/disable service
  
DELETE /api/municipal/services/<service_id>
  → Remove service
```

### View Municipal Data

```
GET /api/municipal/dashboard
  → Municipality-scoped dashboard (properties, taxes, disputes)
  
GET /api/municipal/properties
  → All properties in municipality

GET /api/municipal/lands
  → All lands in municipality

GET /api/municipal/users
  → All users (citizens, businesses, staff) in municipality

GET /api/municipal/taxes/summary
  → Tax collection status
```

### Manage Municipal Staff

```
POST /api/municipal/staff
  → Create new staff member (agent, inspector, etc.)
  → Body: { "username", "email", "password", "role" }
  → Role must be one of: municipal_agent, inspector, finance_officer, etc.

GET /api/municipal/staff
  → List all staff in municipality

PATCH /api/municipal/staff/<user_id>
  → Modify staff details

DELETE /api/municipal/staff/<user_id>
  → Remove staff
```

---

## 7. MODIFIED EXISTING ENDPOINTS (Data Isolation)

### TIB Endpoints (tib.py)

All endpoints NOW include automatic municipality filtering:

```python
@blp.route('/properties', methods=['POST'])
@jwt_required()
@citizen_or_business_required
def declare_property(data):
    """Declare property - MUST be in user's municipality"""
    user_id = get_current_user_id()
    user = User.query.get(user_id)
    
    # Auto-set municipality from user
    property = Property(
        owner_id=user_id,
        commune_id=user.commune_id,  # NEW: Force user's municipality
        street_address=data['street_address'],
        city=data['city'],
        surface_couverte=data['surface_couverte'],
        reference_price_per_m2=data.get('reference_price_per_m2'),  # CHANGED: per m²
        # ...
    )
    
    # Validate reference price is within legal bounds for this municipality
    mun_ref_price = MunicipalReferencePrice.query.filter_by(
        commune_id=user.commune_id,
        tib_category=category
    ).first()
    
    if not (mun_ref_price.legal_min <= property.reference_price_per_m2 <= mun_ref_price.legal_max):
        return jsonify({
            'error': 'Reference price outside legal bounds',
            'legal_range': f"{mun_ref_price.legal_min}-{mun_ref_price.legal_max} TND/m²"
        }), 400
```

### GET Properties (Agent/Inspector/Admin View)

```python
@blp.route('/properties', methods=['GET'])
@jwt_required()
def get_properties():
    """Get properties - scoped to user's municipality"""
    user_id = get_current_user_id()
    user = User.query.get(user_id)
    
    if user.role == UserRole.MINISTRY_ADMIN:
        # See all properties
        properties = Property.query.all()
    elif user.role in [UserRole.MUNICIPAL_ADMIN, UserRole.MUNICIPAL_AGENT, 
                       UserRole.INSPECTOR]:
        # See only their municipality's properties
        properties = Property.query.filter_by(commune_id=user.commune_id).all()
    elif user.role in [UserRole.CITIZEN, UserRole.BUSINESS]:
        # See only their own properties
        properties = Property.query.filter_by(owner_id=user_id).all()
```

### TTNB Endpoints (ttnb.py)

All endpoints NOW include urban zone validation:

```python
@blp.route('/lands', methods=['POST'])
@jwt_required()
@citizen_or_business_required
def declare_land(data):
    """Declare land - requires urban zone"""
    user_id = get_current_user_id()
    user = User.query.get(user_id)
    
    # Validate urban zone is one of 4 official zones
    VALID_ZONES = ['haute_densite', 'densite_moyenne', 'faible_densite', 'peripherique']
    urban_zone = data.get('urban_zone')
    
    if not urban_zone:
        return jsonify({
            'error': 'Urban zone classification required',
            'valid_zones': VALID_ZONES
        }), 400
    
    if urban_zone not in VALID_ZONES:
        return jsonify({
            'error': f'Invalid zone. Must be one of: {", ".join(VALID_ZONES)}'
        }), 400
    
    land = Land(
        owner_id=user_id,
        commune_id=user.commune_id,  # NEW: Force user's municipality
        street_address=data['street_address'],
        city=data['city'],
        surface=data['surface'],
        urban_zone=urban_zone,  # NEW: REQUIRED for tax calculation
        # ...
    )
```

---

## 8. UPDATED TAX CALCULATION (Legal Compliance + Municipal Config)

### TIB Calculation (Legally Correct)

```python
class TaxCalculator:
    @classmethod
    def calculate_tib(cls, property_obj):
        """
        Calculate TIB per Code de la Fiscalité Locale
        using municipality's reference prices and configured services
        """
        
        if property_obj.is_exempt:
            return {'base_amount': 0.0, 'rate_percent': 0.0, 'tax_amount': 0.0}
        
        # Step 1: Determine category from covered surface
        surface = property_obj.surface_couverte
        if surface <= 100:
            category = 1
        elif surface <= 200:
            category = 2
        elif surface <= 400:
            category = 3
        else:
            category = 4
        
        # Step 2: Get reference price for THIS municipality
        ref_price = property_obj.reference_price_per_m2
        if not ref_price:
            return {'error': f'Reference price required for category {category}'}
        
        # Step 3: Calculate Assiette (base) - LEGALLY CORRECT
        assiette = 0.02 * (ref_price * surface)
        
        # Step 4: Count available services in municipality
        services_count = MunicipalServiceConfig.query.filter_by(
            commune_id=property_obj.commune_id,
            is_available=True
        ).count()
        
        # Step 5: Apply service rate - LEGALLY CORRECT (not surcharge)
        if services_count <= 2:
            service_rate = 0.08  # 8%
        elif services_count <= 4:
            service_rate = 0.10  # 10%
        else:
            service_rate = 0.12  # 12%
        
        # Step 6: Calculate final TIB - LEGALLY CORRECT
        tib_amount = assiette * service_rate
        
        return {
            'base_amount': assiette,
            'rate_percent': service_rate * 100,
            'tax_amount': tib_amount,
            'total_amount': tib_amount,
            'category': category,
            'services_count': services_count
        }

    @classmethod
    def calculate_ttnb(cls, land_obj):
        """
        Calculate TTNB per Code de la Fiscalité Locale
        using official zoning tariffs (Décret 2017-396)
        """
        
        if land_obj.is_exempt:
            return {'base_amount': 0.0, 'rate_percent': 0.0, 'tax_amount': 0.0}
        
        # REQUIRED: Urban zone classification
        if not land_obj.urban_zone:
            return {'error': 'Urban zone classification required for TTNB'}
        
        # Official tariffs from Décret 2017-396 (IMMUTABLE)
        ZONE_TARIFFS = {
            'haute_densite': 1.200,      # TND/m²
            'densite_moyenne': 0.800,
            'faible_densite': 0.400,
            'peripherique': 0.200
        }
        
        tariff = ZONE_TARIFFS.get(land_obj.urban_zone)
        if not tariff:
            return {'error': f'Invalid zone: {land_obj.urban_zone}'}
        
        # LEGALLY CORRECT: TTNB = surface × tariff
        ttnb_amount = land_obj.surface * tariff
        
        return {
            'base_amount': ttnb_amount,
            'rate_percent': (tariff / land_obj.surface * 100) if land_obj.surface else 0,
            'tax_amount': ttnb_amount,
            'total_amount': ttnb_amount,
            'zone': land_obj.urban_zone,
            'tariff_per_m2': tariff
        }
```

---

## 9. DATA FILTERING DECORATOR (Automatic)

```python
def municipality_required(f):
    """Decorator: Ensures user has associated municipality"""
    @wraps(f)
    def decorated(*args, **kwargs):
        user_id = get_current_user_id()
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        if user.role == UserRole.MINISTRY_ADMIN:
            # Ministry admin can access everything
            return f(*args, **kwargs)
        
        if not user.commune_id:
            return jsonify({
                'error': 'User not assigned to municipality'
            }), 403
        
        return f(*args, **kwargs)
    return decorated

def municipality_scoped_query(model, user):
    """Helper: Returns query scoped to user's municipality"""
    if user.role == UserRole.MINISTRY_ADMIN:
        return model.query
    else:
        return model.query.filter_by(commune_id=user.commune_id)
```

---

## 10. DATABASE INITIALIZATION (Load communes_tn.csv)

```python
def seed_communes():
    """Load municipalities from communes_tn.csv"""
    import csv
    
    csv_path = 'data/communes_tn.csv'
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            commune = Commune(
                code_municipalite=row['code_municipalite'],
                nom_municipalite_fr=row['nom_municipalite_fr'],
                code_gouvernorat=row['code_gouvernorat'],
                nom_gouvernorat_fr=row['nom_gouvernorat_fr'],
                type_mun_fr=row['type_mun_fr']
            )
            db.session.add(commune)
    
    db.session.commit()
    print(f"✓ Loaded {Commune.query.count()} municipalities")

def seed_ministry_admin():
    """Create initial ministry admin"""
    admin = User(
        username='ministry_admin',
        email='admin@tunisie.tn',
        role=UserRole.MINISTRY_ADMIN,
        commune_id=None  # Nation-wide, no municipality
    )
    admin.set_password('SecurePassword123!')
    db.session.add(admin)
    db.session.commit()
    print("✓ Created MINISTRY_ADMIN user")

def seed_default_reference_prices():
    """Initialize legal min/max ranges for all categories"""
    LEGAL_RANGES = {
        1: (100, 178),
        2: (163, 238),
        3: (217, 297),
        4: (271, 356)
    }
    
    for commune in Commune.query.all():
        for category, (legal_min, legal_max) in LEGAL_RANGES.items():
            # Use midpoint as default
            default_price = (legal_min + legal_max) / 2
            
            ref_price = MunicipalReferencePrice(
                commune_id=commune.id,
                tib_category=category,
                legal_min=legal_min,
                legal_max=legal_max,
                reference_price_per_m2=default_price
            )
            db.session.add(ref_price)
    
    db.session.commit()
    print(f"✓ Initialized reference prices for all categories & communes")

def seed_default_services():
    """Initialize standard municipal services"""
    SERVICES = [
        ('Water', 'water'),
        ('Electricity', 'electricity'),
        ('Sewage', 'sewage'),
        ('Road Maintenance', 'roads'),
        ('Public Lighting', 'lighting'),
        ('Waste Management', 'waste'),
    ]
    
    for commune in Commune.query.all():
        for service_name, service_code in SERVICES:
            config = MunicipalServiceConfig(
                commune_id=commune.id,
                service_name=service_name,
                service_code=service_code,
                is_available=True
            )
            db.session.add(config)
    
    db.session.commit()
    print(f"✓ Initialized default services for all municipalities")
```

---

## 11. DASHBOARD CHANGES

### Ministry Dashboard `/ministry/dashboard`
- Nation-wide revenue chart
- Top 10 municipalities by tax collection
- Recent administrative actions
- System health status

### Municipal Admin Dashboard `/municipal/dashboard`
- Properties declared
- Tax collection by category
- Pending disputes
- Staff activity log
- Reference price settings (editable)

### Agent/Inspector Dashboard `/municipal/dashboard`
- Properties to verify (own municipality only)
- Pending inspections
- Disputed properties
- Recent actions

---

## 12. MIGRATION PATH (From Old to New)

```sql
-- Step 1: Create new tables
CREATE TABLE commune (
    id INTEGER PRIMARY KEY,
    code_municipalite VARCHAR(10) UNIQUE,
    nom_municipalite_fr VARCHAR(255),
    code_gouvernorat VARCHAR(10),
    nom_gouvernorat_fr VARCHAR(255),
    type_mun_fr VARCHAR(50)
);

CREATE TABLE municipal_reference_price (
    id INTEGER PRIMARY KEY,
    commune_id INTEGER FOREIGN KEY,
    tib_category INTEGER,
    legal_min FLOAT,
    legal_max FLOAT,
    reference_price_per_m2 FLOAT,
    set_by_user_id INTEGER,
    set_at DATETIME,
    UNIQUE(commune_id, tib_category)
);

CREATE TABLE municipal_service_config (
    id INTEGER PRIMARY KEY,
    commune_id INTEGER FOREIGN KEY,
    service_name VARCHAR(255),
    service_code VARCHAR(50),
    is_available BOOLEAN,
    configured_by_user_id INTEGER,
    configured_at DATETIME,
    UNIQUE(commune_id, service_code)
);

-- Step 2: Add columns to existing tables
ALTER TABLE user ADD COLUMN commune_id INTEGER FOREIGN KEY;
ALTER TABLE user ADD COLUMN role VARCHAR(50);

ALTER TABLE property ADD COLUMN commune_id INTEGER FOREIGN KEY;
ALTER TABLE property RENAME COLUMN reference_price TO reference_price_per_m2;

ALTER TABLE land ADD COLUMN commune_id INTEGER FOREIGN KEY;
ALTER TABLE land ADD COLUMN urban_zone VARCHAR(50);

-- Step 3: Load communes
INSERT INTO commune FROM communes_tn.csv;

-- Step 4: Set default reference prices & services
CALL seed_default_reference_prices();
CALL seed_default_services();

-- Step 5: Migrate existing data (based on user addresses → match to communes)
-- Complex logic to assign users/properties/lands to communes based on locality
```

---

## 13. AUTHENTICATION FLOW (UPDATED)

### Registration: Citizen
```
POST /auth/register-citizen
Body: { "username", "email", "password", "commune_name_or_code" }
Response: User created with CITIZEN role + matched commune
```

### Registration: Business
```
POST /auth/register-business
Body: { "username", "email", "password", "business_name", "commune_name_or_code" }
Response: User created with BUSINESS role + matched commune
```

### Login (All roles)
```
POST /auth/login
Body: { "username", "password" }
Response: {
  "access_token": "...",
  "refresh_token": "...",
  "user": { "id", "username", "role", "commune_id", "commune_name" }
}
```

### Dashboard Redirect (Client-side)
```javascript
// After successful login:
if (user.role === 'ministry_admin') {
  window.location = '/ministry/dashboard';
} else if (user.role === 'municipal_admin') {
  window.location = `/municipal/${user.commune_id}/dashboard`;
} else if (user.role === 'citizen') {
  window.location = `/citizen/${user.commune_id}/dashboard`;
} // ... etc for other roles
```

---

## 14. SUMMARY OF CHANGES

| Component | Change | Impact |
|-----------|--------|--------|
| **User Model** | Add commune_id | Multi-tenancy support |
| **New Models** | Commune, MunicipalReferencePrice, MunicipalServiceConfig | Municipality-scoped config |
| **TIB Calculation** | Use reference_price_per_m2, correct formula | Legal compliance |
| **TTNB Calculation** | Require urban_zone, use zone tariffs | Legal compliance |
| **Reference Prices** | Per-municipality, within legal bounds | Admin configurability |
| **Services** | Per-municipality, configurable | Local flexibility |
| **Data Filtering** | Auto-scope to commune (except ministry) | Data isolation |
| **Admin Roles** | Two-tier (ministry + municipal) | Governance hierarchy |
| **Endpoints** | New /api/ministry/*, /api/municipal/* | Full admin APIs |
| **Dashboards** | Role-based + municipality-scoped | Appropriate visibility |

---

**Status**: Architecture Ready for Implementation  
**Next Steps**: Database migration, endpoint implementation, dashboard updates

