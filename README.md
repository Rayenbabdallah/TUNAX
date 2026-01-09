# TUNAX - Tunisian Municipal Tax Management System

**Based on Code de la Fiscalité Locale 2025** - Complete implementation of TIB (Taxe sur les Immeubles Bâtis) and TTNB (Taxe sur les Terrains Non Bâtis)

## 📋 Overview

TUNAX is a comprehensive municipal tax management system designed for Tunisia, providing complete compliance with the 2025 Tunisian Tax Code. The system manages property taxes (TIB), land taxes (TTNB), disputes, permits, payments, and participatory budgeting through a microservices architecture with 9 role-based access levels.

### ✨ Key Features

#### Core Tax Management
- **Property Tax (TIB)**: Full Articles 1-34 compliance with 4 coverage bands (≤100, 101-200, 201-400, >400 m²)
- **Land Tax (TTNB)**: Articles 32-33 compliance with exemptions
- **Auto-Calculated Service Rates**: Progressive 8%→10%→12%→14% based on available municipal services (1-2, 3-4, 5-6, 7+ services)
- **Ministry Reference Prices**: Legal min/max bounds per category (nation-wide)
- **Municipal Price Setting**: Admins set exact prices within legal bounds per commune
- **Penalty System**: Automated late payment penalties (5% + 1% monthly, capped at 50%)

#### Authentication & Security
- **9 Role-Based Access Levels**: Citizen, Business, Agent, Inspector, Finance, Contentieux, Urbanism, Municipal Admin, Ministry Admin
- **JWT Authentication**: Token refresh, blacklist, and role-based authorization
- **Two-Factor Authentication (2FA)**: Email-based OTP verification
- **Rate Limiting**: API endpoint protection against abuse
- **Audit Logging**: Complete tracking of all system actions

#### Geolocation & Verification
- **Free Satellite Imagery**: OpenStreetMap, NASA GIBS, USGS Landsat integration
- **Address Validation**: Geocoding with GPS coordinates
- **Field Inspections**: Inspector verification with satellite imagery comparison
- **Document Upload System**: Property/land documents, inspection photos with review workflow

#### Legal Compliance
- **Dispute Resolution**: Articles 23-26, Commission de révision workflow
- **Building Permits**: Article 13 tax payment requirement enforcement
- **Payment Attestations**: Required for permit issuance
- **Tax Exemptions**: Automated validation for eligible properties/lands

#### Citizen Engagement
- **Tax Payment Processing**: Multiple payment methods with tracking
- **Service Reclamations**: Complaint management and assignment
- **Participatory Budget Voting**: Anonymous voting on municipal projects
- **Notification System**: Email alerts for tax deadlines, decisions, and updates

#### Data & Reporting
- **Revenue Analytics**: Finance dashboard with debtors list and collection stats
- **Municipal Statistics**: Property/land counts, payment rates, dispute metrics
- **Searchable Database**: Advanced filters for properties, lands, payments, disputes
- **Export Capabilities**: PDF generation for attestations and reports

## 🏗️ Architecture

```
TUNAX/
├── backend/                    # Flask REST API
│   ├── app.py                  # Main Flask application
│   ├── extensions/             # Database, JWT, API
│   ├── models/                 # SQLAlchemy ORM models
│   ├── schemas/                # Marshmallow validation schemas
│   ├── resources/              # Route blueprints
│   └── utils/                  # Geolocation, calculators, validators
├── frontend/                   # Web Interface
│   ├── common_login/           # Unified login page
│   └── dashboards/             # Role-specific dashboards
├── docker/                     # Containerization
│   ├── Dockerfile
│   ├── docker-compose.yml
│   └── nginx.conf
└── tests/                      # Insomnia API collection

```

## 🚀 Quick Start

### Prerequisites

- Docker & Docker Compose (recommended)
- OR: Python 3.11+, PostgreSQL 15+, Node.js/nginx

### Quick Fresh Start (One Command Block)

**Complete fresh installation with demo data:**

```powershell
cd C:\Users\rayen\Desktop\TUNAX\docker
docker-compose down -v
docker-compose up -d
docker-compose exec backend flask db upgrade
docker-compose exec backend python seed_all.py
```

**Services Available:**
- Frontend: http://localhost:3000
- Backend API: http://localhost:5000
- API Docs: http://localhost:5000/api/v1/docs/swagger-ui
- PostgreSQL: localhost:5432

**Demo Credentials** (Password: `TunaxDemo123!`):
- Citizen: `demo_citizen`
- Business: `demo_business`
- Agent: `demo_agent`
- Inspector: `demo_inspector`
- Finance: `demo_finance`
- Contentieux: `demo_contentieux`
- Urbanism: `demo_urbanism`
- Admin: `demo_admin` (Municipal Admin)
- Ministry: `ministry_admin`

### Option 1: Docker Compose (Recommended)

```bash
# Clone/navigate to project
cd C:\Users\rayen\Desktop\TUNAX\docker

# Start all services
docker-compose up -d

# Run database migrations
docker-compose exec backend flask db upgrade

# Seed essential data (communes + demo users + test resources)
docker-compose exec backend python seed_all.py

# Services will be available:
# - Frontend: http://localhost:3000
# - Backend API: http://localhost:5000
# - API Docs: http://localhost:5000/api/v1/docs
# - PostgreSQL: localhost:5432
```

### Option 2: Manual Setup

```bash
# 1. Create Python virtual environment
python -m venv venv
source venv/Scripts/activate  # Windows

# 2. Install backend dependencies
cd backend
pip install -r requirements.txt

# 3. Setup PostgreSQL
# Create database: tunax_db
# User: tunax_user
# Password: tunax_password

# 4. Initialize database
flask db upgrade

# 5. Seed demo data (communes + users + test resources + sample property)
python seed_all.py

# 6. Run backend
python app.py  # Runs on http://localhost:5000

# 7. Serve frontend (requires nginx or simple server)
# Copy frontend folder to web server root
# Or use: python -m http.server 3000 --directory frontend
```

### Database Management Commands

```powershell
# Check current migration status
docker-compose exec backend flask db current

# Create new migration after model changes
docker-compose exec backend flask db migrate -m "description"

# Apply pending migrations
docker-compose exec backend flask db upgrade

# Rollback one migration
docker-compose exec backend flask db downgrade
```

## 🔐 Authentication

### Register & Login

**Register as Citizen:**
```bash
POST /api/auth/register-citizen
Content-Type: application/json

{
  "username": "ali_mansouri",
  "email": "ali@example.com",
  "password": "SecurePass123",
  "first_name": "Ali",
  "last_name": "Mansouri",
  "cin": "12345678"
}
```

**Register as Business:**
```bash
POST /api/auth/register-business

{
  "username": "zahra_business",
  "email": "zahra@company.tn",
  "password": "SecurePass123",
  "business_name": "Hassan Trading",
  "business_registration": "ABC123456"
}
```

**Login:**
```bash
POST /api/auth/login
{
  "username": "ali_mansouri",
  "password": "SecurePass123"
}

Response:
{
  "access_token": "eyJhbGc...",
  "refresh_token": "eyJhbGc...",
  "role": "citizen",
  "redirect_to": "/dashboard/citizen"
}
```

### Token Management

```bash
# Refresh access token
POST /api/v1/auth/refresh
Authorization: Bearer <refresh_token>

# Logout (revokes token)
POST /api/v1/auth/logout
Authorization: Bearer <access_token>
```

## 📦 API Endpoints

**Complete API Documentation:** http://localhost:5000/api/v1/docs (Swagger/OpenAPI)

### Authentication & 2FA
- `POST /api/v1/auth/register-citizen` - Citizen self-registration
- `POST /api/v1/auth/register-business` - Business self-registration
- `POST /api/v1/auth/login` - User login
- `POST /api/v1/auth/refresh` - Refresh access token
- `POST /api/v1/auth/logout` - Logout & revoke token
- `GET /api/v1/auth/me` - Current user info
- `POST /api/v1/two-factor/enable` - Enable 2FA
- `POST /api/v1/two-factor/verify` - Verify 2FA code
- `POST /api/v1/two-factor/disable` - Disable 2FA

### TIB (Property Tax) Management
- `POST /api/v1/tib/properties` - Declare property (Article 1)
- `GET /api/v1/tib/properties` - List user's properties
- `GET /api/v1/tib/properties/{id}` - Property details
- `PUT /api/v1/tib/properties/{id}` - Update property declaration
- `GET /api/v1/tib/my-taxes` - User's TIB taxes
- `GET /api/v1/tib/calculate` - Calculate TIB preview

### TTNB (Land Tax) Management
- `POST /api/v1/ttnb/lands` - Declare land (Article 33)
- `GET /api/v1/ttnb/lands` - List user's lands
- `GET /api/v1/ttnb/lands/{id}` - Land details
- `PUT /api/v1/ttnb/lands/{id}` - Update land declaration
- `GET /api/v1/ttnb/my-taxes` - User's TTNB taxes
- `GET /api/v1/ttnb/calculate` - Calculate TTNB preview

### Document Management
- `POST /api/v1/documents/declarations/{declaration_id}/documents` - Upload document
- `GET /api/v1/documents/declarations/{declaration_id}/documents` - List documents
- `GET /api/v1/documents/documents/{document_id}/file` - Download document
- `PUT /api/v1/documents/documents/{document_id}/review` - Review document (Agent)
- `DELETE /api/v1/documents/documents/{document_id}` - Delete document

### Payment Processing
- `POST /api/v1/payments/pay` - Record payment
- `GET /api/v1/payments/attestation/{user_id}` - Payment attestation (Article 13)
- `GET /api/v1/payments/my-payments` - Payment history
- `GET /api/v1/payments/check-permit-eligibility/{user_id}` - Check tax status for permits
- `GET /api/v1/payments/receipt/{payment_id}` - Download payment receipt (PDF)

### Dispute & Contentieux (Articles 23-26)
- `POST /api/v1/disputes/` - Submit dispute
- `GET /api/v1/disputes/` - List disputes (role-based)
- `GET /api/v1/disputes/{id}` - Dispute details
- `PATCH /api/v1/disputes/{id}/commission-review` - Commission review
- `PATCH /api/v1/disputes/{id}/decision` - Final decision

### Building Permits (Article 13)
- `POST /api/v1/permits/request` - Request permit
- `GET /api/v1/permits/my-requests` - User's permits
- `GET /api/v1/permits/pending` - Pending permits (Urbanism)
- `PATCH /api/v1/permits/{id}/decide` - Make decision

### Service Reclamations
- `POST /api/v1/reclamations/` - Submit complaint
- `GET /api/v1/reclamations/my-reclamations` - User's complaints
- `GET /api/v1/reclamations/all` - All complaints (Agent)
- `PATCH /api/v1/reclamations/{id}/assign` - Assign to agent
- `PATCH /api/v1/reclamations/{id}/progress` - Update status

### Participatory Budget
- `POST /api/v1/budget/projects` - Create project (Municipal Admin)
- `GET /api/v1/budget/projects` - List projects
- `PATCH /api/v1/budget/projects/{id}/open-voting` - Open voting
- `POST /api/v1/budget/projects/{id}/vote` - Vote (anonymous)
- `PATCH /api/v1/budget/projects/{id}/close-voting` - Close voting

### Municipal Agent (Verification)
- `POST /api/v1/agent/verify/address` - Address validation
- `POST /api/v1/agent/verify/property/{id}` - Verify property declaration
- `POST /api/v1/agent/verify/land/{id}` - Verify land declaration
- `GET /api/v1/agent/pending-verifications` - List pending declarations
- `GET /api/v1/agent/declaration/{id}/documents` - View uploaded documents

### Inspector (Field Inspections)
- `GET /api/v1/inspector/properties/to-inspect` - Properties awaiting inspection
- `GET /api/v1/inspector/lands/to-inspect` - Lands awaiting inspection
- `POST /api/v1/inspector/report` - Submit inspection report
- `GET /api/v1/inspector/property/{id}/satellite-imagery` - Get satellite data
- `POST /api/v1/inspector/inspections/{id}/documents` - Upload inspection photos
- `GET /api/v1/inspector/my-inspections` - Inspection history

### Finance Officer
- `GET /api/v1/finance/debtors` - List tax debtors
- `POST /api/v1/finance/attestation/{user_id}` - Issue payment attestation
- `GET /api/v1/finance/payment-receipts/{user_id}` - Payment receipts
- `GET /api/v1/finance/revenue-report?year=2025` - Revenue statistics
- `GET /api/v1/finance/collection-stats` - Payment collection analytics
- `POST /api/v1/finance/payment-plans/{id}/approve` - Approve payment plan

### Notifications
- `GET /api/v1/notifications/` - List user notifications
- `GET /api/v1/notifications/unread` - Unread notifications count
- `PATCH /api/v1/notifications/{id}/read` - Mark notification as read
- `PATCH /api/v1/notifications/read-all` - Mark all as read
- `DELETE /api/v1/notifications/{id}` - Delete notification

### Ministry (National Level)
- `POST /api/v1/ministry/reference-price-bounds` - Set legal min/max bounds by category (nation-wide)
- `GET /api/v1/ministry/reference-price-bounds` - Get current legal bounds
- `PUT /api/v1/ministry/reference-price-bounds/{category_id}` - Update bounds for category
- `GET /api/v1/ministry/communes` - List all communes with compliance status
- `GET /api/v1/ministry/statistics` - National tax statistics
- `GET /api/v1/ministry/audit/municipalities` - Audit municipal compliance

### Municipal Configuration (Admin)
- `GET /api/v1/municipal/communes` - List all communes
- `GET /api/v1/municipal/communes/{id}` - Commune details
- `POST /api/v1/municipal/communes/{id}/services` - Configure municipal services
- `PUT /api/v1/municipal/communes/{id}/reference-prices` - Set reference prices (within legal bounds)
- `GET /api/v1/municipal/reference-price-bounds` - Get legal min/max bounds by category

### Administrator
- `POST /api/v1/admin/users` - Create user (non-citizen/business)
- `GET /api/v1/admin/users` - List users
- `GET /api/v1/admin/users/{id}` - User details
- `PATCH /api/v1/admin/users/{id}` - Update user
- `DELETE /api/v1/admin/users/{id}` - Deactivate user
- `GET /api/v1/admin/stats` - System statistics
- `GET /api/v1/admin/audit-logs` - System audit logs
- `POST /api/v1/admin/reset-password/{user_id}` - Reset user password

### Search & Reporting
- `GET /api/v1/search/properties` - Search properties (filters: address, owner, status, etc.)
- `GET /api/v1/search/lands` - Search lands
- `GET /api/v1/search/users` - Search users (admin only)
- `GET /api/v1/reports/tax-summary` - Tax summary report
- `GET /api/v1/reports/payment-analysis` - Payment analysis report
- `GET /api/v1/reports/dispute-metrics` - Dispute resolution metrics

## 🧮 Tax Calculation

### TIB (Taxe sur les Immeubles Bâtis) - Articles 1-34

**Implementation Status:** ✅ Complete

**Formula:**
```
Assiette = 0.02 × (reference_price_per_m² × covered_surface)
TIB = Assiette × service_rate
```

**Coverage Categories (4 Bands):**
- Category 1: ≤100 m² → Legal bounds: 100-178 TND/m²
- Category 2: 101-200 m² → Legal bounds: 163-238 TND/m²
- Category 3: 201-400 m² → Legal bounds: 217-297 TND/m²
- Category 4: >400 m² → Legal bounds: 271-356 TND/m²

**Service Rates (Progressive - Article 5):**
- 1-2 services: 8%
- 3-4 services: 10%
- 5-6 services: 12%
- 7+ services: 14%

**Service Count:** Auto-calculated from `MunicipalServiceConfig` (available services per commune)

**Example Calculation:**
```
Property: 150 m² covered surface, Reference Price 200 TND/m², 5 available services
Category: 2 (101-200 m²)
Assiette = 0.02 × (200 × 150) = 600 TND
Service Rate = 12% (5 services fall in 5-6 bracket)
TIB = 600 × 0.12 = 72 TND
```

### TTNB (Taxe sur les Terrains Non Bâtis) - Articles 32-33

**Implementation Status:** ✅ Complete

**Formula:**
```
TTNB = 0.3% × Vénale Value (or Tariff if no declared value)
```

**Exemptions (Article 32):**
- State property
- Public utility land
- Religious buildings
- Educational institutions
- Health facilities
- Agricultural land (conditional)

**Example Calculation:**
```
Land: 5,000 m², Vénale Value 50,000 TND
TTNB = 50,000 × 0.003 = 150 TND
```

### Penalties (Article 19)

**Implementation Status:** ✅ Complete

- **Late Declaration**: 10% of tax amount (one-time)
- **Late Payment**: 5% initial penalty + 1% per month late (capped at 50% total)
- **Automated Calculation**: System auto-applies penalties based on notification date
- **Dispute Adjustment**: Penalties can be waived/reduced through dispute resolution

**Example:**
```
Tax Amount: 1,000 TND, 6 months late
Initial Penalty: 1,000 × 0.05 = 50 TND
Monthly Penalties: 1,000 × 0.01 × 6 = 60 TND
Total Penalty: 50 + 60 = 110 TND
Total Due: 1,000 + 110 = 1,110 TND
```

## 🌍 Free Geolocation APIs

### Used Services

1. **OpenStreetMap Nominatim**
   - Geocoding & reverse geocoding
   - Address validation & suggestions
   - No authentication required
   - Free tier: Unlimited with rate limiting

2. **NASA GIBS Tiles**
   - Daily updated satellite imagery
   - Free access
   - 250m resolution

3. **USGS Landsat**
   - Monthly satellite updates
   - Free public imagery
   - 30m resolution

### Example Usage

```python
# Geocode address
lat, lon = GeoLocator.geocode_address("Rue de la Paix", "Tunis")

# Get satellite imagery info
imagery = SatelliteImagery.get_satellite_imagery_info(lat, lon)

# Validate address
is_valid = GeoLocator.validate_address("Rue Al-Jazira", "Sousse")

# Get suggestions if street not found
suggestions = GeoLocator.get_nearby_streets("Tunis", "Al-Habib")
```

## 👥 Roles & Permissions

### 1. Citizen
- ✅ Self-register with email verification
- ✅ Enable/disable 2FA for account security
- ✅ Declare properties (TIB) and lands (TTNB)
- ✅ Upload supporting documents (title deeds, cadastral plans, tax receipts)
- ✅ View personal tax obligations with detailed breakdowns
- ✅ Make payments and download receipts
- ✅ Submit disputes with document evidence
- ✅ Request permits (if taxes paid - Article 13 enforcement)
- ✅ Submit service complaints
- ✅ Participate in budget voting (anonymous)
- ✅ Receive email notifications for tax deadlines and decisions

### 2. Business Owner
- ✅ Self-register with business registration validation
- ✅ Same capabilities as Citizen
- ✅ Commercial property management
- ✅ Business-specific tax items
- ✅ Multi-property portfolio tracking

### 3. Municipal Agent
- ✅ Verify property declarations with address validation
- ✅ Review uploaded documents (approve/reject with notes)
- ✅ Validate satellite measurements
- ✅ Manage service reclamations (assign, update status)
- ✅ Update property/land verification status
- ✅ Access declaration history and document audit trail

### 4. Inspector
- ✅ Schedule and conduct field inspections
- ✅ Satellite imagery verification (NASA GIBS, USGS Landsat)
- ✅ Generate inspection reports with recommendations
- ✅ Upload inspection photos and measurement reports
- ✅ Flag discrepancies between declared and measured values
- ✅ Access inspection history and statistics

### 5. Finance Officer (Receveur des Finances)
- ✅ View tax debtors list with filtering
- ✅ Issue payment attestations (required for permits)
- ✅ Generate revenue reports by year/quarter/month
- ✅ Track payment collection rates
- ✅ Approve/reject payment plan requests
- ✅ Enforce payment obligations for permit issuance
- ✅ Export financial data for auditing

### 6. Contentieux Officer
- ✅ Process disputes (Article 23) - review and assign
- ✅ Commission de révision coordination (Articles 24-26)
- ✅ Make final ruling decisions with legal justification
- ✅ Handle oppositions and appeals
- ✅ Track dispute resolution metrics
- ✅ Adjust tax amounts based on commission decisions

### 7. Urbanism / Technical Service
- ✅ Validate building permits
- ✅ Enforce tax payment requirement (Article 13)
- ✅ Approve/reject permit requests with reasons
- ✅ Check construction compliance status
- ✅ Coordinate with Finance for tax verification
- ✅ Issue permit certificates

### 8. Municipal Administrator
- ✅ Create/manage all user accounts (except citizens/businesses who self-register)
- ✅ Configure municipal services per commune
- ✅ Set reference prices within legal bounds (100-356 TND/m² by category)
- ✅ View system-wide statistics (properties, lands, payments, disputes)
- ✅ Access complete audit logs
- ✅ System maintenance and configuration
- ✅ Reset user passwords
- ✅ Generate comprehensive reports

### 9. Ministry Administrator (National Level)
- ✅ Set legal reference price bounds (min/max) for all 4 coverage categories
- ✅ Update national tax regulations and compliance requirements
- ✅ Monitor all municipalities for compliance with legal bounds
- ✅ View national-level tax statistics and revenue data
- ✅ Audit municipal tax collection and reporting
- ✅ Access cross-municipality analytics
- ✅ Enforce legal framework (Code de la Fiscalité Locale 2025)
- ✅ Generate national reports for government oversight

## 📊 Data Models

### User
```python
- id: Integer (Primary Key)
- username: String (Unique)
- email: String (Unique)
- password_hash: String
- role: Enum (CITIZEN, BUSINESS, MUNICIPAL_AGENT, INSPECTOR, FINANCE_OFFICER, CONTENTIEUX_OFFICER, URBANISM_OFFICER, MUNICIPAL_ADMIN, MINISTRY_ADMIN)
- first_name, last_name, phone, cin, business_name, business_registration
- is_active: Boolean
- created_at, updated_at: Timestamp
```

### Property (TIB)
```python
- id: Integer (Primary Key)
- owner_id: Foreign Key (User)
- street_address, city, delegation, post_code: String
- latitude, longitude: Float (GPS coordinates)
- surface_couverte, surface_totale: Float (m²)
- affectation: Enum (RESIDENTIAL, COMMERCIAL, INDUSTRIAL, etc.)
- construction_year: Integer
- reference_price: Float
- tax_rate_category: Integer
- service_rate: Integer (0-4)
- status: Enum (DECLARED, VERIFIED, DISPUTED, RESOLVED)
- satellite_verified: Boolean
- is_exempt: Boolean
```

### Tax
```python
- id: Integer (Primary Key)
- property_id / land_id: Foreign Key
- tax_type: Enum (TIB, TTNB)
- tax_year: Integer
- base_amount, rate_percent, tax_amount: Float
- penalty_amount: Float
- total_amount: Float (tax + penalties)
- status: Enum (CALCULATED, NOTIFIED, PAID, DISPUTED)
- notification_date: Timestamp
```

### Dispute
```python
- id: Integer (Primary Key)
- claimant_id: Foreign Key (User)
- dispute_type: Enum (EVALUATION, CALCULATION, EXEMPTION, PENALTY)
- subject, description: String
- status: Enum (SUBMITTED, ACCEPTED, COMMISSION_REVIEW, RESOLVED)
- commission_reviewed: Boolean
- commission_decision, final_decision: Text
- final_amount: Float
- decision_date: Timestamp
```

### Permit
```python
- id: Integer (Primary Key)
- user_id: Foreign Key (User)
- permit_type: Enum (CONSTRUCTION, LOTISSEMENT, OCCUPANCY, SIGNATURE_LEGALIZATION)
- property_id: Foreign Key (Property)
- status: Enum (PENDING, APPROVED, REJECTED, BLOCKED_UNPAID_TAXES)
- taxes_paid: Boolean
- submitted_date, decision_date: Timestamp
```

## 📝 Testing with Insomnia

A complete Insomnia API collection is provided at: `tests/insomnia_collection.json`

### Import Instructions:
1. Open Insomnia
2. Click "Create" → "Import from File"
3. Select `insomnia_collection.json`
4. Configure environment variables:
   - `base_url`: http://localhost:5000
   - `access_token`: From login response
   - `admin_token`, `agent_token`, etc.

### Test Workflows:

**Citizen Tax Workflow:**
1. Register Citizen
2. Login
3. Declare Property (TIB)
4. View My Taxes
5. Make Payment
6. Get Payment Attestation
7. Request Permit

**Dispute Resolution:**
1. Login as Citizen
2. Submit Dispute
3. Login as Contentieux Officer
4. Assign Dispute
5. Commission Review
6. Make Final Decision

**Inspection Workflow:**
1. Login as Inspector
2. Get Properties to Inspect
3. Get Satellite Imagery
4. Submit Inspection Report

## 🔍 Error Handling

All endpoints return standard error responses:

```json
{
  "error": "Error type",
  "message": "Detailed error message"
}
```

**Common Status Codes:**
- 200: Success
- 201: Created
- 400: Bad Request
- 401: Unauthorized
- 403: Forbidden (insufficient permissions)
- 404: Not Found
- 409: Conflict (duplicate data)
- 500: Server Error

## 🛠️ Configuration

### Environment Variables

Create `.env` file in backend:

```bash
DATABASE_URL=postgresql://tunax_user:tunax_password@localhost:5432/tunax_db
JWT_SECRET_KEY=your-secret-key-change-in-production
FLASK_ENV=development
FLASK_DEBUG=True
```

### Database Setup

```sql
CREATE DATABASE tunax_db;
CREATE USER tunax_user WITH PASSWORD 'tunax_password';
ALTER ROLE tunax_user SET client_encoding TO 'utf8';
ALTER ROLE tunax_user SET default_transaction_isolation TO 'read committed';
ALTER ROLE tunax_user SET default_transaction_deferrable TO on;
GRANT ALL PRIVILEGES ON DATABASE tunax_db TO tunax_user;
```

## 📚 API Documentation

Swagger/OpenAPI documentation available at:
```
http://localhost:5000/api/v1/docs
```

### REST Level 3 (HATEOAS)
- Key resources include `_links` with permission-aware and state-based actions for Level 3 REST maturity. See [HATEOAS_IMPLEMENTATION.md](HATEOAS_IMPLEMENTATION.md).

## 🚢 Deployment

### Docker Production Setup

```bash
# Build images
docker-compose -f docker/docker-compose.yml build

# Run with production settings
docker-compose -f docker/docker-compose.yml up -d

# View logs
docker-compose logs -f backend
docker-compose logs -f postgres
```

### Environment for Production

```bash
FLASK_ENV=production
JWT_SECRET_KEY=<strong-random-key-here>
DATABASE_URL=postgresql://user:pass@prod-db-host:5432/tunax_db
```

## 🤝 Contributing

This is a complete production-ready implementation. To extend:

1. Add new property types in `models/property.py`
2. Create new role decorators in `utils/role_required.py`
3. Add endpoints to appropriate resource files
4. Update API tests in `tests/insomnia_collection.json`

## 📄 License

This system implements the official Tunisian Code de la Fiscalité Locale 2025.

## 📞 Support

For issues or clarifications regarding the system implementation, refer to:
- Code de la Fiscalité Locale 2025 (Official PDF)
- API Documentation: `/api/v1/docs`
- Insomnia Collection: `tests/insomnia_collection.json`

---

**Version**: 2.0.0  
**Last Updated**: January 2026  
**Status**: ✅ Production Ready - Feature Complete

## 🎯 Implementation Checklist

### Core Features ✅
- [x] User authentication & JWT token management
- [x] Two-factor authentication (2FA)
- [x] 8 role-based access control levels
- [x] TIB tax calculation (4 coverage bands)
- [x] TTNB tax calculation
- [x] Progressive service rates (8%-14%)
- [x] Municipality reference price configuration
- [x] Legal bounds enforcement (100-356 TND/m²)
- [x] Auto-service count from MunicipalServiceConfig
- [x] Penalty calculation (late payment/declaration)

### Property & Land Management ✅
- [x] Property declaration (TIB)
- [x] Land declaration (TTNB)
- [x] Address validation & geocoding
- [x] GPS coordinates storage
- [x] Document upload system
- [x] Document review workflow
- [x] Multi-document support per declaration
- [x] Exemption validation

### Verification & Inspection ✅
- [x] Agent verification workflow
- [x] Inspector field inspections
- [x] Satellite imagery integration (NASA GIBS, USGS Landsat)
- [x] Inspection photo upload
- [x] Discrepancy flagging
- [x] Measurement validation

### Payments & Finance ✅
- [x] Payment processing
- [x] Payment attestations (Article 13)
- [x] Receipt generation (PDF)
- [x] Debtors list management
- [x] Revenue reporting
- [x] Payment plan support
- [x] Collection statistics

### Disputes & Legal ✅
- [x] Dispute submission
- [x] Commission de révision workflow
- [x] Final decision recording
- [x] Tax amount adjustments
- [x] Appeal handling
- [x] Dispute metrics

### Permits & Urbanism ✅
- [x] Building permit requests
- [x] Tax payment verification (Article 13)
- [x] Permit approval/rejection
- [x] Permit certificate issuance
- [x] Status tracking

### Citizen Engagement ✅
- [x] Service reclamations
- [x] Reclamation assignment
- [x] Status updates
- [x] Participatory budget voting
- [x] Anonymous voting
- [x] Project creation

### Notifications & Communication ✅
- [x] Email notifications
- [x] Tax deadline alerts
- [x] Decision notifications
- [x] Unread count tracking
- [x] Mark as read functionality

### Administration ✅
- [x] User management
- [x] Commune configuration
- [x] Service configuration
- [x] Reference price setting
- [x] System statistics
- [x] Audit logging
- [x] Password reset

### API & Documentation ✅
- [x] RESTful API design
- [x] HATEOAS Level 3 implementation
- [x] Swagger/OpenAPI documentation
- [x] Rate limiting
- [x] Error handling
- [x] Insomnia test collection

### Testing & Quality ✅
- [x] Demo user seeding
- [x] Test data generation
- [x] Commune data seeding
- [x] Resource seeding
- [x] API endpoint testing
- [x] Workflow validation

## 📊 System Statistics

**Total API Endpoints**: 85+  
**Database Models**: 20+  
**User Roles**: 9  
**Supported Tax Types**: 2 (TIB, TTNB)  
**Coverage Categories**: 4  
**Service Rate Tiers**: 4  
**Document Types**: 15+  
**Workflow States**: 50+

## 🔧 Technology Stack

**Backend:**
- Python 3.11+
- Flask 3.0+
- SQLAlchemy (ORM)
- PostgreSQL 15+
- Marshmallow (validation)
- Flask-JWT-Extended
- Flask-Limiter
- Alembic (migrations)

**Frontend:**
- Vanilla JavaScript (ES6+)
- HTML5/CSS3
- Bootstrap 5
- Leaflet.js (maps)
- Chart.js (analytics)

**Infrastructure:**
- Docker & Docker Compose
- Nginx (reverse proxy)
- PostgreSQL (database)
- Ubuntu/Linux deployment

**External APIs:**
- OpenStreetMap Nominatim
- NASA GIBS
- USGS Landsat
- SMTP (email notifications)
