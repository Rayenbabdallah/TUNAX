# TUNAX Architecture - Developer Quick Reference

## Key Principle: Asset-Level Scoping, Not User-Level

Citizens and businesses are **NOT bound to municipalities**. Their properties and lands are.

```
❌ OLD (WRONG):  User.commune_id → User restricted to single municipality
✅ NEW (RIGHT):  Property.commune_id + Land.commune_id → Assets in specific municipality
                User can have properties in MULTIPLE municipalities
```

---

## User Role Quick Reference

| Role | commune_id | Access | Binding |
|------|-----------|--------|---------|
| MINISTRY_ADMIN | NULL | All municipalities | Nation-wide |
| MUNICIPAL_ADMIN | REQUIRED | Single commune | Per-municipality |
| MUNICIPAL_AGENT | REQUIRED | Single commune | Per-municipality |
| INSPECTOR | REQUIRED | Single commune | Per-municipality |
| FINANCE_OFFICER | REQUIRED | Single commune | Per-municipality |
| CONTENTIEUX_OFFICER | REQUIRED | Single commune | Per-municipality |
| URBANISM_OFFICER | REQUIRED | Single commune | Per-municipality |
| CITIZEN | NULL | Multi-commune | Asset-based |
| BUSINESS | NULL | Multi-commune | Asset-based |

---

## JWT Token Structure

### For Citizens/Businesses (commune_id = NULL)
```json
{
  "identity": "123",
  "role": "citizen"
}
```
Note: NO `commune_id` in claims

### For Municipal Staff (commune_id = REQUIRED)
```json
{
  "identity": "456",
  "role": "municipal_agent",
  "commune_id": 1
}
```
Note: `commune_id` always present

### For Ministry Admin (commune_id = NULL)
```json
{
  "identity": "789",
  "role": "ministry_admin"
}
```
Note: NO `commune_id` (doesn't need it)

---

## Data Filtering Patterns

### Pattern 1: Citizen Accessing Own Assets
```python
# Citizens see only THEIR OWN assets across all communes
properties = Property.query.filter_by(owner_id=user_id).all()
lands = Land.query.filter_by(owner_id=user_id).all()
```

### Pattern 2: Municipal Staff Accessing Commune Data
```python
# Staff see all assets in THEIR COMMUNE
properties = Property.query.filter_by(commune_id=user.commune_id).all()
lands = Land.query.filter_by(commune_id=user.commune_id).all()
```

### Pattern 3: Ministry Admin Nation-Wide Access
```python
# Ministry sees EVERYTHING
properties = Property.query.all()
lands = Land.query.all()
```

---

## Endpoint Request Format

### Citizen Declaring Property (MUST specify commune_id)
```bash
POST /api/tib/properties
{
  "street_address": "123 Main St",
  "city": "Tunis",
  "surface_couverte": 200,
  "affectation": "RESIDENTIAL",
  "commune_id": 1,          # ← REQUIRED for citizens
  "reference_price_per_m2": 2500
}
```

### Citizen Declaring Land (MUST specify commune_id)
```bash
POST /api/ttnb/lands
{
  "street_address": "456 Farm Rd",
  "city": "Sfax",
  "surface": 5000,
  "land_type": "AGRICULTURAL",
  "urban_zone": "faible_densite",
  "commune_id": 2,          # ← REQUIRED for citizens
  "latitude": 34.74,
  "longitude": 10.77
}
```

---

## Authorization Decorator Rules

### @municipality_required
Allows access if:
- User is MINISTRY_ADMIN (commune_id = NULL) ✓
- User is CITIZEN/BUSINESS (commune_id = NULL) ✓
- User is municipal staff (commune_id = NOT NULL) ✓

❌ Blocks: Municipal staff WITHOUT commune_id

### @ministry_admin_required
Allows access if:
- User role = MINISTRY_ADMIN only ✓

❌ Blocks: All other roles

### @citizen_or_business_required
Allows access if:
- User role = CITIZEN or BUSINESS ✓

❌ Blocks: All staff roles and admins

---

## Common Mistakes to Avoid

### ❌ MISTAKE 1: Using user.commune_id for citizens
```python
# WRONG - citizens have commune_id=NULL
properties = Property.query.filter_by(
    commune_id=user.commune_id  # NULL for citizens!
).all()
```

### ✅ CORRECT
```python
# RIGHT - use owner_id for citizens
if user.role in [UserRole.CITIZEN, UserRole.BUSINESS]:
    properties = Property.query.filter_by(owner_id=user_id).all()
```

### ❌ MISTAKE 2: Setting citizen commune_id during registration
```python
# WRONG
user = User(
    username=...,
    commune_id=data.get('commune_id'),  # Must be NULL!
    role=UserRole.CITIZEN
)
```

### ✅ CORRECT
```python
# RIGHT
user = User(
    username=...,
    commune_id=None,  # Always NULL for citizens
    role=UserRole.CITIZEN
)
```

### ❌ MISTAKE 3: Requiring commune_id from JWT for citizens
```python
# WRONG - citizens don't have commune_id in claims
user_commune = claims.get('commune_id')  # None for citizens
```

### ✅ CORRECT
```python
# RIGHT - check role and conditionally use commune_id
if user_role in [UserRole.CITIZEN.value, UserRole.BUSINESS.value]:
    # Don't expect commune_id for citizens
    pass
elif user_role in [UserRole.MUNICIPAL_AGENT.value, ...]:
    # Expect commune_id for staff
    user_commune = claims.get('commune_id')
```

---

## Testing Tips

### Test Citizen Multi-Municipality

1. Register citizen: `POST /api/auth/register-citizen` (no commune_id)
2. Declare property in Tunis: `POST /api/tib/properties` with `commune_id=1`
3. Declare land in Sfax: `POST /api/ttnb/lands` with `commune_id=2`
4. Get all properties: `GET /api/tib/properties` (should see both)
5. Get all lands: `GET /api/ttnb/lands` (should see both)

### Test Municipal Staff Single-Municipality

1. Create municipal admin for Tunis: `POST /api/ministry/municipal-admins` with `commune_id=1`
2. Login as municipal admin
3. Get properties: `GET /api/tib/properties` (only Tunis)
4. Try to access Sfax data (should be blocked or filtered)

### Test Ministry Admin Nation-Wide

1. Create ministry admin: Create in DB directly or via endpoint
2. Login as ministry admin
3. Access ministry dashboard: `GET /api/ministry/dashboard`
4. View all municipalities: `GET /api/ministry/municipalities`
5. See all properties: `GET /api/tib/properties` (all of Tunisia)

---

## Database Schema Reminders

### Property Model
```python
class Property:
    owner_id = ForeignKey('users.id')        # Who owns it
    commune_id = ForeignKey('commune.id')    # Where it is (REQUIRED)
    # citizen can have properties in multiple communes
```

### Land Model
```python
class Land:
    owner_id = ForeignKey('users.id')        # Who owns it
    commune_id = ForeignKey('commune.id')    # Where it is (REQUIRED)
    # citizen can have lands in multiple communes
```

### User Model
```python
class User:
    role = Enum(UserRole)                    # 9 roles
    commune_id = ForeignKey('commune.id')    # CONDITIONAL:
                                             # NULL for citizen/business
                                             # REQUIRED for staff
                                             # NULL for ministry_admin
```

---

## API Endpoints Summary

### Auth (No municipality binding for citizens)
- `POST /api/auth/register-citizen` - commune_id NOT included
- `POST /api/auth/register-business` - commune_id NOT included
- `POST /api/auth/login` - commune_id conditional in response
- `POST /api/auth/refresh` - commune_id conditional in claims

### TIB (Property tax - asset-level scoping)
- `POST /api/tib/properties` - REQUIRES commune_id from data
- `GET /api/tib/properties` - Filters by role (owner_id for citizens, commune_id for staff)

### TTNB (Land tax - asset-level scoping)
- `POST /api/ttnb/lands` - REQUIRES commune_id from data
- `GET /api/ttnb/lands` - Filters by role (owner_id for citizens, commune_id for staff)

### Ministry (Nation-wide admin)
- `GET /api/ministry/dashboard` - All data
- `POST /api/ministry/municipal-admins` - Create commune-bound admins
- `GET /api/ministry/municipalities` - All communes

### Municipal (Per-municipality admin)
- `GET /api/municipal/dashboard` - Single commune data
- `GET /api/municipal/reference-prices` - Commune-specific
- `GET /api/municipal/staff` - Commune staff only

### Inspector (Municipality-specific)
- `GET /api/inspector/properties/to-inspect` - Commune filtered
- `GET /api/inspector/lands/to-inspect` - Commune filtered

---

## Deployment Checklist

Before pushing to production:

- [ ] All 7 modified files reviewed
- [ ] Unit tests pass
- [ ] Citizen registration creates user with commune_id=NULL
- [ ] Citizens can declare properties in multiple communes
- [ ] JWT tokens conditional for commune_id
- [ ] Inspector views municipality-filtered
- [ ] Ministry admin sees nation-wide data
- [ ] Database migrations applied
- [ ] Communes seed data loaded

---

## Quick Debug Checklist

**Issue**: Citizen can't declare property
1. Check: User.commune_id is NULL ✓
2. Check: Request includes commune_id ✓
3. Check: JWT doesn't require commune_id ✓
4. Check: @municipality_required allows citizens ✓

**Issue**: Inspector sees wrong municipality
1. Check: User.commune_id is set correctly ✓
2. Check: Query filters by user.commune_id ✓
3. Check: No "get all" query without filtering ✓

**Issue**: Citizen sees other user's property
1. Check: Filtering by owner_id not commune_id ✓
2. Check: Property.owner_id matches user_id ✓
3. Check: No commune-based filtering for citizens ✓

---

**Version**: 2.0 - Multi-Municipality Corrected Architecture  
**Last Updated**: After Phase 2 Architecture Review  
**Status**: ✅ Production Ready
