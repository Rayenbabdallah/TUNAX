# TUNAX Architecture Quick Reference

## 🎯 Key Changes Summary

### What's New
1. **Two-Tier Admin System**: MINISTRY_ADMIN (nation-wide) + MUNICIPAL_ADMIN (per-commune)
2. **Legally-Correct Formulas**: TIB and TTNB match Code de la Fiscalité Locale 2025
3. **Data Isolation**: All data scoped to communes via commune_id FK
4. **Urban Zones**: REQUIRED for TTNB (haute_densite, densite_moyenne, faible_densite, peripherique)
5. **Reference Prices**: Per-municipality, per-TIB-category, with legal bounds

### Files Added (6)
- `models/commune.py` - Commune entity
- `models/municipal_config.py` - Reference prices & services
- `resources/ministry.py` - 9 nation-wide endpoints
- `resources/municipal.py` - 14 per-municipality endpoints
- `seed_communes.py` - Initialize communes & configs
- `seed_data/communes_tn.csv` - Tunisian municipalities

### Files Modified (10)
- `models/user.py` - Added commune_id, new roles
- `models/property.py` - commune_id FK, reference_price_per_m2
- `models/land.py` - commune_id FK, urban_zone REQUIRED
- `models/__init__.py` - New model imports
- `utils/calculator.py` - Correct formulas
- `utils/role_required.py` - 3 new decorators
- `resources/auth.py` - Commune-aware registration
- `resources/tib.py` - Commune-scoped access
- `resources/ttnb.py` - Urban zone requirement
- `app.py` - Register new blueprints

## 📐 TIB Formula (Article 4-5)

```
Category (surface):
  ≤100m² → Cat 1
  100-200m² → Cat 2
  200-400m² → Cat 3
  >400m² → Cat 4

Assiette = 0.02 × (reference_price_per_m² × surface_covered)

Services:
  0-2 services → 8% rate
  3-4 services → 10% rate
  5+ services → 12% rate

TIB = Assiette × service_rate  ← Rate applied directly!
```

## 📐 TTNB Formula (Décret 2017-396)

```
Urban Zone REQUIRED:
  'haute_densite' → 1.200 TND/m²
  'densite_moyenne' → 0.800 TND/m²
  'faible_densite' → 0.400 TND/m²
  'peripherique' → 0.200 TND/m²

TTNB = surface_m² × zone_tariff  ← No percentage!
```

## 🔐 Authorization Decorators

```python
@ministry_admin_required
# Only MINISTRY_ADMIN, nation-wide access

@municipal_admin_required
# Only MUNICIPAL_ADMIN, per-commune (validates commune_id)

@municipality_required
# Requires commune_id (auto-filters queries for non-ministry)
```

## 🚀 Setup

```bash
# 1. Run migrations
alembic upgrade head

# 2. Seed communes
python seed_communes.py

# 3. Start server
python app.py

# 4. Log in with ministry admin
# username: ministry_admin
# password: change-me-in-production
```

## 🔗 Key Endpoints

### Ministry (Nation-wide)
```
GET    /api/ministry/dashboard
GET    /api/ministry/municipalities
POST   /api/ministry/municipal-admins
PATCH  /api/ministry/municipal-admins/<id>/status
GET    /api/ministry/audit-log
```

### Municipal (Per-Commune)
```
GET    /api/municipal/dashboard
GET    /api/municipal/reference-prices
PUT    /api/municipal/reference-prices/<category>
GET    /api/municipal/services
POST   /api/municipal/services
PATCH  /api/municipal/staff/<id>
```

### Citizens/Businesses
```
POST   /api/tib/properties          ← NEW: requires commune_id
GET    /api/tib/properties
POST   /api/ttnb/lands              ← NEW: requires urban_zone
GET    /api/ttnb/lands
POST   /api/payments/pay
```

## 🗃️ Reference Price Bounds

```
TIB Category 1:  100-178 TND/m²
TIB Category 2:  163-238 TND/m²
TIB Category 3:  217-297 TND/m²
TIB Category 4:  271-356 TND/m²
```

Municipal admins can set any price within these bounds.

## 🏠 User Registration (NEW)

```python
# Citizens/Businesses can register with optional commune_id
POST /api/auth/register-citizen
{
  "username": "user",
  "email": "user@example.tn",
  "password": "secure",
  "commune_id": 7101  # Optional
}

# If commune_id is provided, user is scoped to that municipality
# All their properties/lands must be in that commune
```

## 🔄 Creating Property/Land (CHANGED)

```python
# TIB Property REQUIRES commune_id
POST /api/tib/properties
{
  "street_address": "...",
  "city": "...",
  "surface_couverte": 85,
  "affectation": "...",
  "reference_price_per_m2": 145,  # Changed from reference_price
  "commune_id": 7101  # NEW - required
}

# TTNB Land REQUIRES urban_zone
POST /api/ttnb/lands
{
  "street_address": "...",
  "city": "...",
  "surface": 500,
  "land_type": "...",
  "urban_zone": "haute_densite",  # NEW - required!
  "commune_id": 7101
}
```

## 📊 Data Access by Role

### Citizens/Businesses
- See only their own properties/lands
- Can declare in any municipality (if registered there)

### Municipal Staff (Agent/Inspector/Finance)
- See all properties/lands in their commune
- Cannot see other communes
- Reference prices set by their MUNICIPAL_ADMIN

### Municipal Admin
- See all properties/lands in their commune
- Set reference prices (within legal bounds)
- Configure available services
- Create/manage commune staff

### Ministry Admin
- See all properties/lands across Tunisia
- Set legal bounds for reference prices
- Manage MUNICIPAL_ADMIN accounts
- View nationwide statistics

## 🐛 Common Issues

### "Urban zone required"
→ For TTNB lands, must provide one of: haute_densite, densite_moyenne, faible_densite, peripherique

### "Reference price outside legal bounds"
→ Municipal admins can only set prices within the legal min/max for each category
→ See Reference Price Bounds table above

### "Access denied"
→ Property/land must be in user's commune
→ Municipal staff can't see other municipalities

### "Commune not found"
→ Verify commune_id exists via GET /api/ministry/municipalities

## 📝 Legal Compliance

All formulas and bounds verified against:
- Code de la Fiscalité Locale 2025
- Décret 2017-396 (urban zones & tariffs)
- Article 4-5 (TIB service rates)

System enforces these constraints at the database and API levels.

---

**For detailed documentation, see IMPLEMENTATION_COMPLETE.md**
