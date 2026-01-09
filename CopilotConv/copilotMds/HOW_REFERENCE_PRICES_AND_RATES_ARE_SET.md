# How Reference Prices and Zone Rates Are Set in TUNAX

## Overview
The TUNAX system uses a **two-tier approach** for setting reference prices and tax rates:

1. **Per-Property/Land**: Citizens/businesses provide their own reference prices when declaring assets
2. **System-Wide Tariffs**: Fixed tax calculation rates from a YAML configuration file

---

## 1. Reference Prices (TIB - Taxe sur les Immeubles Bâtis)

### 1.1 How Reference Prices Are Set NOW

**Current Method: User-Provided During Declaration**

When a property owner declares a property (POST `/api/tib/properties`), they provide:

```json
{
  "street_address": "123 Rue de la Liberte",
  "city": "Tunis",
  "surface_couverte": 120,
  "surface_totale": 200,
  "affectation": "residential",
  "construction_year": 2015,
  "reference_price": 100000,      // ← User provides this
  "service_rate": 3                // ← User specifies number of services
}
```

**Storage Location**: [Property Model](backend/models/property.py#L49)
```python
reference_price = db.Column(db.Float)  # Prix de référence from Article 4
```

**Validation**: Currently **minimal**
- No minimum value check (see PROJECT_REVIEW.md line 271)
- No maximum check
- No geographic zone validation
- No historical price database integration

### 1.2 How Reference Prices Are Used in Calculations

The reference price drives the **base tax calculation** per Article 4:

**Formula** (in [calculator.py](backend/utils/calculator.py#L140)):
```
Base Amount = Reference Price × 0.02 × Surface Category Multiplier
Tax Amount = Base Amount × (1 + Service Rate%)
```

**Example**:
- Reference Price: 100,000 TND
- Surface: 120 m² → Category B multiplier = 1.25
- Base = 100,000 × 0.02 × 1.25 = 2,500 TND
- Service Rate: 3 (10%) → Tax = 2,500 × 1.10 = 2,750 TND

### 1.3 Updating Reference Prices

Users can update reference prices via PUT endpoint [tib.py#L183-L228](backend/resources/tib.py#L183-L228):

```python
PUT /api/tib/properties/<property_id>

{
  "reference_price": 120000  // Updated value
}
```

**Important**: Updating reference price does NOT automatically recalculate tax. Tax recalculation occurs during:
- Annual renewal (via `/api/renewal/properties/<id>/renew`)
- Manual tax recalculation (not currently exposed in API)

---

## 2. Tax Rates (Both TIB and TTNB)

### 2.1 TIB Tax Rates - Fixed in YAML Configuration

Tax rates are **NOT per-zone** but rather based on:
1. **Surface Category** (Articles 4)
2. **Number of Municipal Services** (Article 5)

All rates are defined in [tariffs_2025.yaml](backend/resources/tariffs_2025.yaml):

#### Surface Categories (Article 4)
```yaml
TIB:
  surface_categories:
    - { min: 0,    max: 50,   label: A, multiplier: 1.00 }
    - { min: 50,   max: 100,  label: B, multiplier: 1.25 }
    - { min: 100,  max: 200,  label: C, multiplier: 1.50 }
    - { min: 200,  max: 9.0e9, label: D, multiplier: 1.75 }
```

**How it works** (in [calculator.py#L97-L102](backend/utils/calculator.py#L97-L102)):
```python
def _get_surface_multiplier(cls, surface_m2: float) -> float:
    for bracket in cfg['TIB']['surface_categories']:
        if bracket['min'] <= surface_m2 < bracket['max']:
            return float(bracket['multiplier'])
```

#### Service Rates (Article 5)
```yaml
TIB:
  service_rates:
    - { min_services: 0, rate_percent: 8 }   # 0-2 services → 8%
    - { min_services: 3, rate_percent: 10 }  # 3-4 services → 10%
    - { min_services: 5, rate_percent: 12 }  # 5-6 services → 12%
    - { min_services: 7, rate_percent: 14 }  # 7+ services → 14%
```

**How it works** (in [calculator.py#L104-L111](backend/utils/calculator.py#L104-L111)):
```python
def _get_service_rate(cls, num_services: int) -> float:
    applicable = 0
    for band in cfg['TIB']['service_rates']:
        if num_services >= int(band['min_services']):
            applicable = float(band['rate_percent'])
    return applicable / 100.0
```

### 2.2 TTNB Tax Rate - Fixed in YAML

Lands are taxed at a **uniform rate** per Article 33:

```yaml
TTNB:
  base_rate_percent: 0.3
```

Formula: `Tax = Vénale Value × 0.3%` (or `Tariff Value × 0.3%` if no market value)

**Storage** (in [calculator.py#L41](backend/utils/calculator.py#L41)):
```python
cls._cfg['TTNB'].setdefault('base_rate_percent', 0.3)
```

---

## 3. Current Gaps and Limitations

### 🔴 **NO Zone-Based Rate System**
- Rates are **not geographic**
- All properties in all zones pay identical rates
- **No urban vs. rural differentiation**
- **No city/district override rates**

### 🔴 **NO Official Reference Price Database**
- No integration with government cadastre (CNPU) reference values
- No historical price trends
- **Users can declare any reference price** (vulnerability)

### 🔴 **NO Admin Interface for Tariff Management**
- [admin.py](backend/resources/admin.py) has NO endpoints for updating tariffs
- Changing rates requires **editing YAML file directly** and restarting backend

### 🔴 **NO Rate Validation**
- Users could declare reference_price = 0 (triggering 0 tax)
- [PROJECT_REVIEW.md#L271](PROJECT_REVIEW.md#L271): "No validation that reference_price > 0"

---

## 4. How to Change Rates NOW

### Method 1: Edit YAML File (Current Way)

**File**: [tariffs_2025.yaml](backend/resources/tariffs_2025.yaml)

```bash
# 1. Edit the YAML file
nano backend/resources/tariffs_2025.yaml

# 2. Change values, e.g., update service rates:
TIB:
  service_rates:
    - { min_services: 0, rate_percent: 9 }   # Changed from 8% to 9%
    - { min_services: 3, rate_percent: 11 }  # Changed from 10% to 11%

# 3. Restart backend
docker-compose restart backend
# or: python backend/app.py
```

**Pros**:
- ✅ Changes apply immediately on backend restart
- ✅ Version-controlled in git

**Cons**:
- ❌ Requires backend restart
- ❌ No audit trail
- ❌ No rollback mechanism
- ❌ Error-prone (YAML syntax errors = crash)

### Method 2: Programmatic (Currently Not Implemented)

To implement admin UI for rate changes, you would need:

```python
@admin_bp.route('/tariffs/surface-multipliers', methods=['PUT'])
@jwt_required()
@admin_required
def update_surface_multipliers():
    """Update surface category multipliers"""
    data = request.get_json()  # New multipliers
    # 1. Validate
    # 2. Store in database (not YAML)
    # 3. Clear calculator cache
    # 4. Log change (audit trail)
    # 5. Return confirmation
```

---

## 5. Recommended Improvements

### Priority 1: Add Zone-Based Rates
```yaml
TIB:
  zones:
    tunis_center:
      city: "Tunis"
      delegation: "Centre"
      rate_multiplier: 1.0
    tunis_suburbs:
      city: "Tunis"
      delegation: ["Ariana", "Ben Arous", "Manouba"]
      rate_multiplier: 0.8
    sousse:
      city: "Sousse"
      rate_multiplier: 0.7
```

### Priority 2: Add Reference Price Validation
```python
# In validator
@staticmethod
def validate_reference_price(price):
    if not price or price <= 0:
        return False, "Reference price must be > 0"
    if price > 100_000_000:  # Max limit
        return False, "Reference price exceeds maximum"
    return True, None
```

### Priority 3: Add Admin API for Tariff Management
```python
# Admin endpoints:
PUT /api/admin/tariffs/surface-multipliers/<zone>
PUT /api/admin/tariffs/service-rates
PUT /api/admin/tariffs/ttnb-rate
GET /api/admin/tariffs/history  # Audit log
```

### Priority 4: Integrate with CNPU Cadastre
```python
# Real reference prices from official source
GET /api/cadastre/reference-price?address=...&city=...
```

---

## 6. Summary Table

| Aspect | Current Implementation | Location | Can User Change? | Admin Change Method |
|--------|----------------------|----------|------------------|-------------------|
| Reference Price (TIB) | User-provided float | Property model, tib.py | ✅ Yes (PUT endpoint) | Direct edit (no API) |
| Surface Multipliers | YAML config (1.00-1.75) | tariffs_2025.yaml | ❌ No | File edit + restart |
| Service Rates | YAML config (8%-14%) | tariffs_2025.yaml | ❌ No | File edit + restart |
| TTNB Rate | YAML config (0.3%) | tariffs_2025.yaml | ❌ No | File edit + restart |
| Geographic Zones | Not implemented | None | N/A | Not available |
| Audit Trail | Not implemented | None | N/A | Not available |
| Rate History | Not implemented | None | N/A | Not available |

---

## 7. Code References

**TIB Calculation** (Articles 4-5):
- Calculation engine: [calculator.py#L124-L170](backend/utils/calculator.py#L124-L170)
- Declaration endpoint: [tib.py#L30-L112](backend/resources/tib.py#L30-L112)
- Property model: [property.py#L49-L51](backend/models/property.py#L49-L51)

**TTNB Calculation** (Article 33):
- Calculation engine: [calculator.py#L172-L199](backend/utils/calculator.py#L172-L199)
- Declaration endpoint: [ttnb.py#L18-L100](backend/resources/ttnb.py#L18-L100)
- Land model: [land.py#L42-L44](backend/models/land.py#L42-L44)

**Tariff Configuration**:
- YAML file: [tariffs_2025.yaml](backend/resources/tariffs_2025.yaml)
- Loading logic: [calculator.py#L19-L48](backend/utils/calculator.py#L19-L48)

---

**Generated**: December 2024  
**Status**: Current implementation verified
