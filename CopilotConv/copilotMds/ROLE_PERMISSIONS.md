# Role-Based Access Control (RBAC) - API Endpoints

This document maps all API endpoints to the user roles that can access them.

## User Roles

| Role | Description |
|------|-------------|
| **Public** | No authentication required |
| **Citizen** | Regular citizens declaring personal properties/lands |
| **Business** | Business entities declaring commercial properties |
| **Municipal Agent** | Municipal staff handling declarations, exemptions, permits |
| **Municipal Admin** | Municipality administrator managing local services |
| **Finance** | Finance department staff handling payments and attestations |
| **Inspector** | Field inspectors verifying satellite imagery |
| **Ministry Admin** | Central government oversight of all municipalities |
| **Contentieux** | Legal department handling disputes |
| **Urbanism** | Urban planning department managing construction permits |

---

## Endpoint Permissions by Role

### 🌐 Public Endpoints (No Authentication)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check |
| GET | `/api/docs/swagger-ui` | Swagger API documentation |
| GET | `/api/public/tax-rates` | Get current tax tariff rates |
| POST | `/api/public/calculator` | Estimate tax before declaration |
| GET | `/api/public/communes` | List all municipalities |
| GET | `/api/public/localities` | Get localities for a commune |
| GET | `/api/public/document-requirements` | List required documents for a commune/type |

---

### 👤 Citizen & Business Endpoints

#### Authentication
| Method | Endpoint | Description | Roles |
|--------|----------|-------------|-------|
| POST | `/api/auth/register` | Register new account | Public |
| POST | `/api/auth/login` | Login and get JWT token | Public |
| GET | `/api/auth/profile` | Get user profile | Citizen, Business |
| PUT | `/api/auth/profile` | Update profile | Citizen, Business |

#### TIB (Property Tax)
| Method | Endpoint | Description | Roles |
|--------|----------|-------------|-------|
| POST | `/api/tib/properties` | Declare new property | Citizen, Business |
| GET | `/api/tib/properties` | List user's properties | Citizen, Business |
| GET | `/api/tib/properties/{id}` | Get property details | Citizen, Business (owner only) |
| PUT | `/api/tib/properties/{id}` | Update property | Citizen, Business (owner only) |
| DELETE | `/api/tib/properties/{id}` | Delete property | Citizen, Business (owner only) |
| GET | `/api/tib/properties/{id}/taxes` | Get property taxes | Citizen, Business (owner only) |
| GET | `/api/tib/my-taxes` | Get all user's TIB taxes | Citizen, Business |

#### TTNB (Land Tax)
| Method | Endpoint | Description | Roles |
|--------|----------|-------------|-------|
| POST | `/api/ttnb/lands` | Declare new land | Citizen, Business |
| GET | `/api/ttnb/lands` | List user's lands | Citizen, Business |
| GET | `/api/ttnb/lands/{id}` | Get land details | Citizen, Business (owner only) |
| PUT | `/api/ttnb/lands/{id}` | Update land | Citizen, Business (owner only) |
| DELETE | `/api/ttnb/lands/{id}` | Delete land | Citizen, Business (owner only) |
| GET | `/api/ttnb/lands/{id}/taxes` | Get land taxes | Citizen, Business (owner only) |
| GET | `/api/ttnb/my-taxes` | Get all user's TTNB taxes | Citizen, Business |

#### Payments
| Method | Endpoint | Description | Roles |
|--------|----------|-------------|-------|
| POST | `/api/payments/pay` | Pay tax | Citizen, Business |
| GET | `/api/payments/my-payments` | List user's payments | Citizen, Business |
| GET | `/api/payments/{id}/receipt` | Download payment receipt (PDF) | Citizen, Business |
| GET | `/api/payments/permit-check/{tax_id}` | Check permit eligibility | Citizen, Business |

#### Permits (Citizen Access)
| Method | Endpoint | Description | Roles |
|--------|----------|-------------|-------|
| POST | `/api/permits/request` | Request construction permit | Citizen, Business |
| GET | `/api/permits/my-requests` | List user's permit requests | Citizen, Business |
| GET | `/api/permits/{id}` | Get permit details | Citizen, Business (owner) |

#### Reclamations (Complaints)
| Method | Endpoint | Description | Roles |
|--------|----------|-------------|-------|
| POST | `/api/reclamations` | Submit reclamation | Citizen, Business |
| GET | `/api/reclamations/my-reclamations` | Get user's reclamations | Citizen, Business |
| GET | `/api/reclamations/{id}` | Get reclamation details | Citizen, Business (owner), Agent |

#### Documents
| Method | Endpoint | Description | Roles |
|--------|----------|-------------|-------|
| POST | `/api/v1/documents/declarations/{id}/documents` | Upload document | Citizen, Business (owner) |
| GET | `/api/v1/documents/declarations/{id}/documents` | List documents | Citizen, Business (owner), Agent |

#### Two-Factor Authentication (All Authenticated Users)
| Method | Endpoint | Description | Roles |
|--------|----------|-------------|-------|
| POST | `/api/2fa/setup` | Setup 2FA | All authenticated users |
| POST | `/api/2fa/enable` | Enable 2FA | All authenticated users |
| POST | `/api/2fa/disable` | Disable 2FA | All authenticated users |
| GET | `/api/2fa/status` | Get 2FA status | All authenticated users |
| POST | `/api/2fa/regenerate-backup-codes` | Regenerate backup codes | All authenticated users |

#### Dashboards
| Method | Endpoint | Description | Roles |
|--------|----------|-------------|-------|
| GET | `/api/dashboard/citizen-summary` | Citizen dashboard summary | Citizen, Business |

---

### 🏛️ Municipal Agent Endpoints

All citizen/business endpoints PLUS:

#### Exemptions
| Method | Endpoint | Description | Roles |
|--------|----------|-------------|-------|
| GET | `/api/agent/exemptions` | List exemption requests | Municipal Agent |
| GET | `/api/agent/exemptions/{id}` | Get exemption details | Municipal Agent |
| PATCH | `/api/agent/exemptions/{id}` | Review exemption (approve/reject) | Municipal Agent |

#### Reclamations Management
| Method | Endpoint | Description | Roles |
|--------|----------|-------------|-------|
| GET | `/api/reclamations/all` | List all reclamations | Municipal Agent |
| PATCH | `/api/reclamations/{id}/assign` | Assign reclamation | Municipal Agent |
| PATCH | `/api/reclamations/{id}/progress` | Update progress | Municipal Agent |

#### Documents Review
| Method | Endpoint | Description | Roles |
|--------|----------|-------------|-------|
| PATCH | `/api/v1/documents/documents/{id}/review` | Review document | Municipal Agent |
| GET | `/api/v1/documents/documents/{id}/file` | Download document | Municipal Agent |

---

### 🏢 Municipal Admin Endpoints

All municipal agent endpoints PLUS:

#### Municipal Management
| Method | Endpoint | Description | Roles |
|--------|----------|-------------|-------|
| GET | `/api/municipal/dashboard` | Municipal dashboard | Municipal Admin |
| GET | `/api/municipal/reference-prices` | Get reference prices | Municipal Admin |
| PUT | `/api/municipal/reference-prices` | Update reference prices | Municipal Admin |
| GET | `/api/municipal/services` | List municipal services | Municipal Admin |
| POST | `/api/municipal/services` | Create service | Municipal Admin |
| PATCH | `/api/municipal/services/{id}` | Update service | Municipal Admin |
| DELETE | `/api/municipal/services/{id}` | Delete service | Municipal Admin |
| GET | `/api/municipal/document-requirements` | List document requirements | Municipal Admin |
| POST | `/api/municipal/document-requirements` | Create document requirement | Municipal Admin |
| PUT | `/api/municipal/document-requirements/{id}` | Update document requirement | Municipal Admin |
| DELETE | `/api/municipal/document-requirements/{id}` | Delete document requirement | Municipal Admin |
| GET | `/api/municipal/properties` | List properties in municipality | Municipal Admin |
| GET | `/api/municipal/lands` | List lands in municipality | Municipal Admin |

#### Staff Management
| Method | Endpoint | Description | Roles |
|--------|----------|-------------|-------|
| POST | `/api/municipal/staff` | Create staff account | Municipal Admin |
| GET | `/api/municipal/staff` | List staff | Municipal Admin |
| PATCH | `/api/municipal/staff/{id}` | Update staff | Municipal Admin |
| DELETE | `/api/municipal/staff/{id}` | Delete staff | Municipal Admin |

---

### 💰 Finance Department Endpoints

#### Payment Management
| Method | Endpoint | Description | Roles |
|--------|----------|-------------|-------|
| GET | `/api/payments/attestation/{user_id}` | Issue non-debt certificate | Finance |

#### Financial Reports
| Method | Endpoint | Description | Roles |
|--------|----------|-------------|-------|
| GET | `/api/finance/revenue-report` | Revenue report | Finance |
| GET | `/api/finance/payment-history` | Payment history | Finance |

---

### 🔍 Inspector Endpoints

#### Inspection Queue
| Method | Endpoint | Description | Roles |
|--------|----------|-------------|-------|
| GET | `/api/inspector/properties/to-inspect` | Properties awaiting inspection | Inspector |
| GET | `/api/inspector/lands/to-inspect` | Lands awaiting inspection | Inspector |

#### Inspection Reports
| Method | Endpoint | Description | Roles |
|--------|----------|-------------|-------|
| POST | `/api/inspector/report` | Submit inspection report | Inspector |
| GET | `/api/inspector/report/{id}` | Get inspection report | Inspector |
| GET | `/api/inspector/satellite-imagery/{id}` | Get satellite imagery | Inspector |
| GET | `/api/inspector/my-reports` | Get inspector's reports | Inspector |

#### Dashboards
| Method | Endpoint | Description | Roles |
|--------|----------|-------------|-------|
| GET | `/api/dashboard/inspector-workload` | Inspector workload | Inspector |

---

### 🏛️ Ministry Admin Endpoints (Central Government)

#### Nationwide Oversight
| Method | Endpoint | Description | Roles |
|--------|----------|-------------|-------|
| GET | `/api/ministry/dashboard` | National dashboard | Ministry Admin |
| GET | `/api/ministry/municipalities` | List all municipalities | Ministry Admin |
| GET | `/api/ministry/municipal-admins` | List municipal admins | Ministry Admin |
| POST | `/api/ministry/municipal-admins` | Create municipal admin | Ministry Admin |
| PATCH | `/api/ministry/municipal-admins/{id}` | Update admin status | Ministry Admin |

#### National Reports
| Method | Endpoint | Description | Roles |
|--------|----------|-------------|-------|
| GET | `/api/ministry/reference-prices` | National reference prices | Ministry Admin |
| POST | `/api/ministry/reference-prices` | Update reference prices | Ministry Admin |
| GET | `/api/ministry/revenue-report` | National revenue report | Ministry Admin |
| GET | `/api/ministry/audit-log` | Audit log | Ministry Admin |

---

### ⚖️ Contentieux (Legal) Endpoints

#### Dispute Management
| Method | Endpoint | Description | Roles |
|--------|----------|-------------|-------|
| GET | `/api/dispute/cases` | List dispute cases | Contentieux |
| GET | `/api/dispute/cases/{id}` | Get case details | Contentieux |
| PATCH | `/api/dispute/cases/{id}` | Update case status | Contentieux |
| POST | `/api/dispute/cases/{id}/ruling` | Add ruling | Contentieux |

---

### 🏗️ Urbanism Department Endpoints

#### Construction Permits
| Method | Endpoint | Description | Roles |
|--------|----------|-------------|-------|
| GET | `/api/permits/pending` | List pending permits | Urbanism |
| GET | `/api/permits/{id}` | Get permit details | Urbanism, Owner |
| PATCH | `/api/permits/{id}/decide` | Approve/reject permit | Urbanism |
| GET | `/api/permits/blocked` | List blocked permits (Article 13) | Urbanism |

---

### 🔎 Search Endpoints (All Authenticated Users)

| Method | Endpoint | Description | Roles |
|--------|----------|-------------|-------|
| GET | `/api/search/properties` | Search properties | All authenticated |
| GET | `/api/search/lands` | Search lands | All authenticated |

---

### 📊 Dashboard Endpoints

| Method | Endpoint | Description | Roles |
|--------|----------|-------------|-------|
| GET | `/api/dashboard/citizen-summary` | Citizen dashboard | Citizen, Business |
| GET | `/api/dashboard/admin-overview` | Admin dashboard | Municipal Admin, Ministry Admin |
| GET | `/api/dashboard/inspector-workload` | Inspector dashboard | Inspector |

---

## Role Hierarchy

```
Ministry Admin (Full Access)
    └─ Municipal Admin (Municipality Scope)
           ├─ Municipal Agent (Declaration Management)
           ├─ Finance (Payment Management)
           ├─ Inspector (Field Verification)
           ├─ Contentieux (Legal Disputes)
           └─ Urbanism (Construction Permits)
                  └─ Citizen / Business (Self-service)
```

---

## Authentication Requirements

### Public Routes (No Token Required)
- Health check
- Swagger docs
- Public tax calculator
- Tax rates
- Commune/locality lists
- Registration
- Login

### Protected Routes (JWT Token Required)
All other endpoints require:
```http
Authorization: Bearer <access_token>
```

### Role-Based Access
After JWT validation, endpoints check user role:
- **Decorators:** `@citizen_or_business_required`, `@agent_required`, `@inspector_required`, etc.
- **Error:** Returns `403 Forbidden` if role mismatch

---

## Usage Examples

### Citizen Flow
```
1. POST /api/auth/register → Create account
2. POST /api/auth/login → Get token
3. POST /api/tib/properties → Declare property
4. POST /api/payments/pay → Pay tax
5. GET /api/payments/{id}/receipt → Download receipt
```

### Municipal Agent Flow
```
1. POST /api/auth/login → Get token
2. GET /api/agent/exemptions → Review requests
3. PATCH /api/agent/exemptions/{id} → Approve/reject
4. GET /api/reclamations/all → View complaints
```

### Inspector Flow
```
1. POST /api/auth/login → Get token
2. GET /api/inspector/properties/to-inspect → Get queue
3. GET /api/inspector/satellite-imagery/{id} → View imagery
4. POST /api/inspector/report → Submit report
```

### Ministry Admin Flow
```
1. POST /api/auth/login → Get token
2. GET /api/ministry/dashboard → National overview
3. GET /api/ministry/municipalities → All municipalities
4. POST /api/ministry/municipal-admins → Create admin
```

---

## Testing in Insomnia

The Insomnia collection at `tests/insomnia_collection.json` contains:
- Pre-configured requests for all roles
- Environment variables for `base_url` and `access_token`
- Demo credentials for each role

**Import the collection and test with:**
```
Demo Credentials:
- Citizen: citizen_demo / TunaxDemo123!
- Municipal Admin: admin_demo / TunaxDemo123!
- Ministry Admin: ministry_admin / TunaxDemo123!
- Inspector: inspector_demo / TunaxDemo123!
```
