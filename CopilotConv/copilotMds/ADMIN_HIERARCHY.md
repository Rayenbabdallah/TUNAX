# Admin Hierarchy & Permissions

## Architecture

### Two-Tier Admin System

```
MINISTRY_ADMIN (Super Admin)
├── Can create MUNICIPAL_ADMINS
├── Can view all data nation-wide
├── Can create policies and reference prices
└── Endpoints: /api/ministry/*

    ↓ (creates)

    MUNICIPAL_ADMIN (Municipality Admin)
    ├── Can create STAFF (agents, inspectors, etc.)
    ├── Can view only their municipality's data
    ├── Can manage reference prices for their municipality
    └── Endpoints: /api/admin/*
    
        ↓ (creates)
        
        STAFF MEMBERS
        ├── MUNICIPAL_AGENT
        ├── INSPECTOR
        ├── FINANCE_OFFICER
        ├── CONTENTIEUX_OFFICER
        └── URBANISM_OFFICER
```

---

## Endpoints & Authorization

### MINISTRY ADMIN ONLY - `/api/ministry/*`

**Who can access**: MINISTRY_ADMIN role only

**Endpoints**:
- `POST /api/ministry/municipal-admins` - Create municipal admin (requires commune_id)
- `GET /api/ministry/municipal-admins` - List all municipal admins
- `PATCH /api/ministry/municipal-admins/<id>/status` - Enable/disable admin
- `GET /api/ministry/dashboard` - Nation-wide statistics
- `GET /api/ministry/municipalities` - List all communes
- `GET /api/ministry/municipalities/<id>` - Commune details
- `GET /api/ministry/audit-log` - All administrative actions
- `GET /api/ministry/reports/reference-prices` - All reference prices
- `GET /api/ministry/reports/revenue` - All revenue data

**Authorization**: `@ministry_admin_required` decorator

---

### MUNICIPALITY ADMIN ONLY - `/api/municipal/*`

**Who can access**: MUNICIPAL_ADMIN role only (tied to specific commune)

**Endpoints**:
- `GET /api/municipal/dashboard` - Municipality statistics
- `POST /api/municipal/staff` - Create staff member (agents, inspectors, etc.)
- `GET /api/municipal/staff` - List staff in municipality
- `PATCH /api/municipal/staff/<id>` - Update staff member
- `DELETE /api/municipal/staff/<id>` - Deactivate staff member

**Authorization**: `@municipal_admin_required` decorator

**Important**: Municipality admin can ONLY:
- Create staff for their own municipality
- View staff in their own municipality
- Cannot create other admins
- Cannot access ministry endpoints

---

## Creation Flow

### Step 1: Ministry Admin Creates Municipal Admin

```bash
POST /api/ministry/municipal-admins
{
  "username": "fatima_tunis",
  "email": "fatima@tunis.gov.tn",
  "password": "SecurePass123!",
  "first_name": "Fatima",
  "last_name": "Ben Ali",
  "commune_id": 1  ← Required (Tunis)
}
```

**Response**:
```json
{
  "message": "Municipal admin created successfully",
  "user_id": 123,
  "username": "fatima_tunis",
  "role": "municipal_admin",
  "commune_id": 1,
  "commune_name": "Tunis"
}
```

**Result**: User with MUNICIPAL_ADMIN role is created and tied to Tunis (commune_id=1)

---

### Step 2: Municipal Admin Creates Staff

```bash
POST /api/admin/staff
Authorization: Bearer <MUNICIPAL_ADMIN_TOKEN>
{
  "username": "ahmed_inspector",
  "email": "ahmed@tunis.gov.tn",
  "password": "StrongPass123!",
  "first_name": "Ahmed",
  "last_name": "Inspector",
  "role": "inspector"  ← Only allowed roles: agent, inspector, finance_officer, contentieux_officer, urbanism_officer
}
```

**Response**:
```json
{
  "message": "Staff member created successfully",
  "user_id": 124,
  "username": "ahmed_inspector",
  "role": "inspector",
  "commune_id": 1,  ← Automatically set to admin's commune
  "commune_name": "Tunis"
}
```

**Result**: Inspector is automatically tied to Tunis (same as admin's commune)

---

## Key Rules

### ✅ ALLOWED

✅ Ministry admin creates municipal admin  
✅ Ministry admin creates municipal admin with specific commune  
✅ Municipal admin creates staff for their municipality  
✅ Municipal admin views dashboard for their municipality  
✅ Municipal admin lists staff in their municipality  
✅ Municipal admin deactivates staff in their municipality  

### ❌ NOT ALLOWED

❌ Municipal admin creates other municipal admins  
❌ Municipal admin accesses `/api/ministry/*` endpoints  
❌ Municipal admin creates staff for OTHER municipalities  
❌ Staff members create other staff  
❌ Citizens create anything  
❌ Municipal admin sees data from other municipalities  

---

## Data Isolation

### By Municipality

**Municipal Admin can see**:
- Properties in their municipality
- Lands in their municipality
- Taxes for assets in their municipality
- Staff members in their municipality
- Revenue from their municipality

**Municipal Admin CANNOT see**:
- Properties in other municipalities
- Lands in other municipalities
- Data from other municipalities
- Other municipal admins' data

### Nation-Wide (Ministry)

**Ministry Admin can see**:
- All properties across Tunisia
- All lands across Tunisia
- All municipalities
- All municipal admins
- All revenue
- All administrative actions

---

## JWT Claims

### Ministry Admin JWT
```json
{
  "identity": "789",
  "role": "ministry_admin"
  // No commune_id - nation-wide access
}
```

### Municipal Admin JWT
```json
{
  "identity": "123",
  "role": "municipal_admin",
  "commune_id": 1  ← Tied to Tunis
}
```

### Staff JWT
```json
{
  "identity": "456",
  "role": "inspector",
  "commune_id": 1  ← Tied to Tunis (same as creating admin)
}
```

---

## Dashboard Access

### Redirect on Login

**Ministry Admin** → `/dashboards/admin/` (ministry dashboard)  
**Municipal Admin** → `/dashboards/admin/` (municipality dashboard)  
**Citizens** → `/dashboards/citizen/`  
**Inspectors** → `/dashboards/inspector/`  
**Etc** → Respective dashboards

---

## Important: Only Ministry Creates Admins

```
┌─────────────────────────────────────────┐
│  ONLY MINISTRY ADMIN CAN DO THIS:       │
│  POST /api/ministry/municipal-admins    │
│                                         │
│  - Create new municipal admins          │
│  - Assign them to specific communes     │
│  - Enable/disable municipal admins      │
└─────────────────────────────────────────┘

┌─────────────────────────────────────────┐
│  Municipal Admin CANNOT:                 │
│  - Create other municipal admins        │
│  - Access /api/ministry/* endpoints     │
│  - View other municipalities' data      │
│  - Delete/disable other admins          │
└─────────────────────────────────────────┘
```

---

## Testing the Hierarchy

### 1. Ministry Admin Creates Municipal Admin for Tunis

```bash
curl -X POST http://localhost:5000/api/ministry/municipal-admins \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <MINISTRY_TOKEN>" \
  -d '{
    "username": "fatima",
    "email": "fatima@tunis.gov.tn",
    "password": "Pass123!",
    "commune_id": 1
  }'
```

### 2. Municipal Admin Creates Inspector

```bash
curl -X POST http://localhost:5000/api/admin/staff \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <FATIMA_TOKEN>" \
  -d '{
    "username": "ahmed",
    "email": "ahmed@tunis.gov.tn",
    "password": "Pass123!",
    "role": "inspector"
  }'
```

### 3. Municipal Admin Views Dashboard

```bash
curl -X GET http://localhost:5000/api/admin/dashboard \
  -H "Authorization: Bearer <FATIMA_TOKEN>"
```

### 4. Municipal Admin Lists Staff

```bash
curl -X GET http://localhost:5000/api/admin/staff \
  -H "Authorization: Bearer <FATIMA_TOKEN>"
```

---

## Summary

✅ **Ministry Admin Dashboard**: `/api/ministry/dashboard`  
✅ **Municipality Admin Dashboard**: `/api/admin/dashboard`  
✅ **Only Ministry Can Create Admins**: `/api/ministry/municipal-admins`  
✅ **Only Admin Can Create Staff**: `/api/admin/staff`  
✅ **Complete Data Isolation**: Municipality admins see only their data  
✅ **Role-Based Access Control**: Decorators enforce permissions

---

**Status**: ✅ Admin hierarchy properly implemented  
**Date**: After admin endpoint reorganization  
**Version**: 2.0 - Two-Tier Admin System
