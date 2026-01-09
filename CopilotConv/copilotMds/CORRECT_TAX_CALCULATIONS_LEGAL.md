# CORRECT Tunisian Tax Calculations - Code de la Fiscalité Locale 2025

**Generated**: December 14, 2025  
**Status**: Legal Compliance Analysis

---

## ⚠️ CRITICAL: Current TUNAX Implementation is INCORRECT

The current TUNAX system violates the Code de la Fiscalité Locale in **fundamental ways**:

| Aspect | Current (WRONG) | Legal (CORRECT) |
|--------|-----------------|-----------------|
| **TIB Base Value** | Single lump-sum reference_price | Reference price **PER m²** in legal ranges |
| **TIB Categories** | 4 surface bands with multipliers (A/B/C/D) | 4 categories with **legal min/max ranges per m²** |
| **TTNB Calculation** | 0.3% of vénale/tariff value | **Zoning tariff × surface** (1.200, 0.800, 0.400, 0.200 TND/m²) |
| **TTNB Dependency** | Based on market value | Based on **urban zoning only** |
| **Data Source** | User-provided estimates | **Government decrees** |

---

## 1️⃣ TAXE SUR LES IMMEUBLES BÂTIS (TIB) - CORRECT VERSION

### 1.1 Legal Framework

**Source**: Code de la Fiscalité Locale, Articles 1-34

TIB is **NOT** a percentage of market value.

TIB is calculated using:
- A **reference price per m²** (fixed by government decree)
- This reference price has **legal minimum and maximum bounds**
- A fixed **2% rate** applied to the calculated base
- An additional **service-based rate** (8%, 10%, 12%, 14%)

### 1.2 Property Categories (by covered surface)

| Category | Covered Surface Range | Legal Reference Price Range (TND/m²) |
|----------|----------------------|--------------------------------------|
| **1** | ≤ 100 m² | **100 – 178 TND/m²** |
| **2** | 100 – 200 m² | **163 – 238 TND/m²** |
| **3** | 200 – 400 m² | **217 – 297 TND/m²** |
| **4** | > 400 m² | **271 – 356 TND/m²** |

**Key**: The reference price is **PER SQUARE METER**, not total.

### 1.3 Step-by-Step TIB Calculation

#### Step 1: Determine Property Category
```
IF covered_surface ≤ 100 m²
  → Category 1
ELSE IF covered_surface ≤ 200 m²
  → Category 2
ELSE IF covered_surface ≤ 400 m²
  → Category 3
ELSE
  → Category 4
```

#### Step 2: Reference Price (Prix de Référence Fiscal)
```
Must be WITHIN the legal range for the category.

IF property_owner_provides_reference_price:
  IF NOT (legal_min ≤ provided_price ≤ legal_max):
    REJECT: "Price outside legal bounds"
  ELSE:
    reference_price_per_m2 = provided_price
ELSE:
  STATE: "Reference price must be between [legal_min] and [legal_max] TND/m²"
  CALCULATE: Use midpoint or state it cannot be calculated
```

#### Step 3: Calculate Tax Base (Assiette Fiscale)
```
Assiette TIB = 2% × (Reference price per m² × Covered surface)

Formula:
Assiette = 0.02 × (ref_price_per_m2 × surface_covered)

Unit: TND
```

#### Step 4: Apply Service-Based Rate (Tax Rate)

| Number of Municipal Services | Tax Rate |
|------------------------------|----------|
| 1–2 services | **8%** |
| 3–4 services | **10%** |
| > 4 services | **12%** |
| > 4 services + additional | **14%** |

⚠️ **CRITICAL**: The service rate percentage IS the tax itself, NOT a surcharge.

```
Final TIB = Assiette TIB × Service Rate (as decimal)

Where Service Rate is:
  0.08 (8%) if 1-2 services
  0.10 (10%) if 3-4 services
  0.12 (12%) if more than 4 services
  0.14 (14%) if more than 4 services + additional

NEVER use: Assiette × (1 + rate) ❌
ALWAYS use: Assiette × rate ✓
```

### 1.4 Worked Example: TIB Calculation

**Given**:
- Covered surface: 150 m²
- Reference price: 200 TND/m² (user provides; legal range for Category 2 is 163–238)
- Municipal services available: 3

**Step 1**: Category 2 (100 ≤ 150 ≤ 200)

**Step 2**: Reference price = 200 TND/m² (valid: 163 ≤ 200 ≤ 238 ✓)

**Step 3**: Calculate base
```
Assiette TIB = 0.02 × (200 × 150)
            = 0.02 × 30,000
            = 600 TND
```

**Step 4**: Apply service rate (3 services → 10% = 0.10)
```
Final TIB = 600 × 0.10
          = 60 TND
```

**Answer**: **TIB = 60 TND per year** ✓

---

## 2️⃣ TAXE SUR LES TERRAINS NON BÂTIS (TTNB) - CORRECT VERSION

### 2.1 Legal Framework

**Source**: Code de la Fiscalité Locale, Articles 32-33  
**Decree**: Décret gouvernemental n°2017-396 du 28 mars 2017

TTNB applies **ONLY** to:
- **Non-built land** (terrain non bâti)
- Located **within municipal boundaries**
- Identified in the cadastral register

TTNB calculation is **independent** of municipal services or market value.

### 2.2 Urban Zoning Tariffs (Fixed by Decree)

TTNB is calculated based on **urban zone classification** only:

| Urban Zone Classification | Tariff (TND/m² per year) |
|---------------------------|--------------------------|
| **Zone à forte densité urbaine** | **1.200 TND/m²** |
| **Zone à densité moyenne** | **0.800 TND/m²** |
| **Zone à faible densité** | **0.400 TND/m²** |
| **Zone périphérique / non urbanisée** | **0.200 TND/m²** |

**Source**: Décret gouvernemental n°2017-396 du 28 mars 2017 (immutable unless new decree issued)

### 2.3 Step-by-Step TTNB Calculation

#### Step 1: Verify Land is Non-Built
```
IF property_is_constructed OR property_has_building:
  → NOT eligible for TTNB
  RETURN: "This property has built structures; use TIB instead"
ELSE:
  → Proceed with TTNB
```

#### Step 2: Identify Urban Zone
```
Zone must be determined from:
1. Municipal cadastral records
2. Urban planning documents
3. Official zoning maps

Possible zones:
  - "Zone à forte densité urbaine"        → 1.200 TND/m²
  - "Zone à densité moyenne"              → 0.800 TND/m²
  - "Zone à faible densité"               → 0.400 TND/m²
  - "Zone périphérique / non urbanisée"   → 0.200 TND/m²

IF zone NOT identified:
  RETURN: "Calculation not possible. Zone classification required."
```

#### Step 3: Calculate TTNB
```
TTNB = Surface area (m²) × Zoning tariff (TND/m²)

Formula:
TTNB = surface_m2 × tariff_per_m2

Unit: TND per year
```

#### Step 4: No Service Rate Applied
```
TTNB does NOT depend on number of municipal services.
Final TTNB = Result from Step 3 (no adjustments)
```

### 2.4 Worked Example: TTNB Calculation

**Given**:
- Land surface: 5,000 m²
- Land type: Non-built agricultural land
- Location: Suburb of Sousse
- Urban zone: "Zone à faible densité"

**Step 1**: Land is non-built ✓

**Step 2**: Zone identified as "Zone à faible densité" → tariff = 0.400 TND/m²

**Step 3**: Calculate
```
TTNB = 5,000 × 0.400
     = 2,000 TND
```

**Step 4**: No service adjustment

**Answer**: **TTNB = 2,000 TND per year**

---

## 3️⃣ CRITICAL RULES & CONSTRAINTS

### Rule 1: Never Mix TIB and TTNB
```
Each property is EITHER:
- A built property → Calculate TIB
- OR a non-built land → Calculate TTNB

NOT both.
```

### Rule 2: Reference Price for TIB Must Be Within Legal Bounds
```
IF user provides reference_price_per_m2:
  Category = Determine from covered_surface
  legal_min, legal_max = Get from law
  
  IF reference_price_per_m2 < legal_min:
    REJECT with message: "Below minimum {legal_min} TND/m²"
  ELSE IF reference_price_per_m2 > legal_max:
    REJECT with message: "Exceeds maximum {legal_max} TND/m²"
  ELSE:
    ACCEPT and use provided value
```

### Rule 3: TTNB Requires Zone Identification
```
IF zone is unknown:
  DO NOT calculate 0.3% of an estimated value
  INSTEAD: Return error "Zone classification required"
```

### Rule 4: Missing Data = Calculation Impossible
```
For TIB:
  - IF covered_surface is missing → "Cannot calculate"
  - IF reference_price_per_m2 is missing AND no legal default → State legal range only

For TTNB:
  - IF surface_area is missing → "Cannot calculate"
  - IF zone is unknown → "Cannot calculate; zone required"
```

---

## 4️⃣ COMPARISON: Current Implementation vs. Legal Requirements

### TIB Calculation Error

**Current (WRONG)**:
```python
# From backend/utils/calculator.py line ~140
base_amount = float(property_obj.reference_price) * 0.02 * surface_mult

# Problems:
# 1. reference_price is treated as a TOTAL value, not per m²
# 2. surface_mult is arbitrary multiplier (1.00-1.75), not legal categories
# 3. No validation against legal min/max ranges
# 4. Formula doesn't match Code de la Fiscalité Locale
```

**Correct**:
```
Assiette TIB = 0.02 × (reference_price_per_m2 × covered_surface)

WHERE:
- reference_price_per_m2 must be in legal range for category
- covered_surface determines category (≤100, 100-200, 200-400, >400)
- Categories have FIXED legal min/max ranges, not arbitrary multipliers
```

### TTNB Calculation Error

**Current (WRONG)**:
```python
# From backend/utils/calculator.py line ~180
tax_amount = float(land_obj.venale_value or land_obj.tariff_value) * 0.003

# Problems:
# 1. Uses 0.3% rate (completely fabricated)
# 2. Based on market value (venale_value), not zoning
# 3. No zone classification
# 4. Ignores Décret 2017-396 entirely
```

**Correct**:
```
TTNB = surface_m2 × tariff_per_m2

WHERE tariff_per_m2 is:
- 1.200 if "Zone à forte densité urbaine"
- 0.800 if "Zone à densité moyenne"
- 0.400 if "Zone à faible densité"
- 0.200 if "Zone périphérique / non urbanisée"

(From Décret gouvernemental n°2017-396)
```

---

## 5️⃣ DATA MODEL REQUIREMENTS FOR CORRECTNESS

### For TIB (Built Properties)

**Required fields**:
```
1. covered_surface (m²)          [determines category]
2. reference_price_per_m2 (TND)  [must be within legal bounds]
3. num_municipal_services (int)  [determines service rate: 1-2, 3-4, >4]
```

**Validation**:
```
- covered_surface > 0
- reference_price_per_m2 within legal range for category
- num_municipal_services >= 0
```

### For TTNB (Non-Built Land)

**Required fields**:
```
1. surface_area (m²)             [for tax calculation]
2. urban_zone (string)           [must be one of 4 official zones]
3. is_within_municipality (bool) [must be true for TTNB to apply]
```

**Validation**:
```
- surface_area > 0
- urban_zone in ["Zone à forte densité urbaine", 
                   "Zone à densité moyenne",
                   "Zone à faible densité",
                   "Zone périphérique / non urbanisée"]
- is_within_municipality = true
```

---

## 6️⃣ CALCULATION EXAMPLES WITH LEGAL COMPLIANCE

### Example 1: Small Apartment (TIB)

**Facts**:
- Covered surface: 85 m²
- Owner provides: 150 TND/m²
- Municipal services: 2 (water, electricity)

**Step 1**: Category determination
```
85 m² ≤ 100 m²
→ Category 1
```

**Step 2**: Validate reference price
```
Legal range for Category 1: 100–178 TND/m²
Provided: 150 TND/m²
150 ∈ [100, 178] ✓ VALID
```

**Step 3**: Calculate base
```
Assiette = 0.02 × (150 × 85)
         = 0.02 × 12,750
         = 255 TND
```

**Step 4**: Apply service rate
```
2 services → 8% rate = 0.08
Final TIB = 255 × 0.08 = 20.40 TND
```

**RESULT**: **TIB = 20.40 TND/year** ✓

---

### Example 2: Medium House (TIB)

**Facts**:
- Covered surface: 250 m²
- Owner provides: 250 TND/m²
- Municipal services: 4 (water, electricity, sewage, roads)

**Step 1**: Category determination
```
200 < 250 ≤ 400
→ Category 3
```

**Step 2**: Validate reference price
```
Legal range for Category 3: 217–297 TND/m²
Provided: 250 TND/m²
250 ∈ [217, 297] ✓ VALID
```

**Step 3**: Calculate base
```
Assiette = 0.02 × (250 × 250)
         = 0.02 × 62,500
         = 1,250 TND
```

**Step 4**: Apply service rate
```
4 services → 10% rate = 0.10
Final TIB = 1,250 × 0.10 = 125 TND
```

**RESULT**: **TIB = 125 TND/year** ✓

---

### Example 3: Agricultural Land (TTNB)

**Facts**:
- Surface area: 2 hectares = 20,000 m²
- Urban zone: "Zone à faible densité"
- Within municipality: Yes
- Is non-built: Yes

**Step 1**: Verify non-built
```
No structures on land ✓
```

**Step 2**: Zone identification
```
Zone = "Zone à faible densité"
Tariff = 0.400 TND/m²
```

**Step 3**: Calculate
```
TTNB = 20,000 × 0.400
     = 8,000 TND
```

**Step 4**: No adjustments
```
TTNB is final
```

**RESULT**: **TTNB = 8,000 TND/year** ✓

---

### Example 4: Missing Data (Calculation Not Possible)

**Facts**:
- Land surface: 5,000 m²
- Urban zone: UNKNOWN
- Is non-built: Yes

**Analysis**:
```
Cannot calculate TTNB without zone.

RETURN: "Calculation not possible. 
         Urban zone classification required to apply zoning tariff.
         Please provide zone from: 
         - Zone à forte densité urbaine (1.200 TND/m²)
         - Zone à densité moyenne (0.800 TND/m²)
         - Zone à faible densité (0.400 TND/m²)
         - Zone périphérique / non urbanisée (0.200 TND/m²)"
```

---

## 7️⃣ SUMMARY OF LEGAL DEFINITIONS

### TIB (Taxe sur les Immeubles Bâtis)

| Aspect | Definition |
|--------|-----------|
| **What it taxes** | Built properties (immeubles bâtis) |
| **Base value** | Reference price **per m²** (fixed by decree) |
| **Categories** | 4 categories by covered surface (≤100, 100-200, 200-400, >400) |
| **Legal ranges** | Category 1: 100–178; Cat 2: 163–238; Cat 3: 217–297; Cat 4: 271–356 (all TND/m²) |
| **Base formula** | Assiette = 2% × (ref_price_per_m² × surface_covered) |
| **Tax rate** | Service-based: 8%, 10%, 12%, 14% (NOT surcharge) |
| **Final formula** | TIB = Assiette × rate (as decimal, e.g., 0.10 for 10%) |
| **Data source** | Government decree (reference ranges); user provides value within range |

### TTNB (Taxe sur les Terrains Non Bâtis)

| Aspect | Definition |
|--------|-----------|
| **What it taxes** | Non-built land (terrains non bâtis) in municipalities |
| **Base value** | Zoning tariff (TND/m²) from Décret 2017-396 |
| **Zoning categories** | 4 zones: forte densité (1.200), moyenne (0.800), faible (0.400), périphérique (0.200) |
| **Data source** | Urban planning classification (FIXED by decree, not user-provided) |
| **Formula** | TTNB = surface_m² × tariff_per_m² |
| **Service dependency** | NONE (not applicable) |
| **Final amount** | Direct result from formula |

---

## 8️⃣ IMMEDIATE ACTIONS NEEDED

### Current Code Errors to Fix

1. **Property Model** ([backend/models/property.py](backend/models/property.py))
   - ❌ Current: Single `reference_price` field
   - ✅ Should have: `reference_price_per_m2` (with validation against legal min/max)

2. **Land Model** ([backend/models/land.py](backend/models/land.py))
   - ❌ Current: `vénale_value`, `tariff_value` fields
   - ✅ Should have: `urban_zone` (enumeration of 4 official zones)

3. **Calculator** ([backend/utils/calculator.py](backend/utils/calculator.py))
   - ❌ Current TIB: Uses arbitrary multipliers and wrong formula
   - ❌ Current TTNB: Uses 0.3% of market value
   - ✅ Should implement exact legal formulas above

4. **Tariff Configuration** ([backend/resources/tariffs_2025.yaml](backend/resources/tariffs_2025.yaml))
   - ❌ Current: Invented multipliers and 0.3% rate
   - ✅ Should contain: Legal ranges for TIB, official tariffs for TTNB zones

---

## 9️⃣ CONCLUSION

The current TUNAX implementation **fundamentally violates the Code de la Fiscalité Locale** by:

1. ❌ Using market values instead of legal reference price ranges for TIB
2. ❌ Using arbitrary multipliers instead of legal category bounds
3. ❌ Calculating TTNB as 0.3% of value instead of zoning-based tariff per m²
4. ❌ Ignoring Décret gouvernemental n°2017-396 for TTNB zoning

**Legal compliance requires** using the exact formulas, categories, and tariffs defined in the Code de la Fiscalité Locale 2025 and referenced decrees—not inventions or market values.

---

**Document prepared by**: Legal Compliance Review  
**Date**: December 14, 2025  
**Status**: Reference Implementation (Corrected)
