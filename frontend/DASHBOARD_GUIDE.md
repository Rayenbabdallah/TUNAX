# Frontend Dashboard Guide - TUNAX System

## Overview

The TUNAX system provides 8 complete, role-specific dashboards for managing municipal taxes in Tunisia. Each dashboard is optimized for the unique workflow and responsibilities of each user role.

## Dashboard Locations

All dashboards are accessible via:
```
http://localhost:3000/dashboard/{role}.html
```

## User Roles & Dashboards

### 1. **Citizen Dashboard**
📁 File: `frontend/dashboards/citizen/index.html`

**Purpose:** Self-serve tax management for individual taxpayers

**Key Features:**
- Property (TIB) declarations and management
- Land (TTNB) declarations for non-built land ownership
- Tax calculation and payment tracking
- Payment history and receipts
- Dispute submission (Article 23)
- Building permit requests (enforces Article 13: taxes must be paid)
- Service complaint submissions
- Budget voting participation

**Tax Calculations:**
- TIB: Based on property surface area + service availability bands (Articles 1-34)
- TTNB: Based on urban zoning tariffs per Décret 2017-396 (official TND/m²)
- Penalties: 10% for late declaration; late payment is 1.25% per month starting Jan 1 of the second year after the tax year (N+2)

**Access Control:** Citizens can only view their own properties, taxes, and permits

---

### 2. **Business Dashboard**
📁 File: `frontend/dashboards/business/index.html`

**Purpose:** Tax management for business entities

**Key Features:**
- TTNB land parcel declarations (0.3% tax)
- Tax payment processing with attestation tracking
- Building permits for commercial development (Article 13 enforced)
- Dispute resolution for contested taxes
- Participatory budget voting
- Payment methods: bank transfer, check, cash

**Business-Specific Rules:**
- Businesses primarily declare non-built land (TTNB)
- Must pay all taxes before obtaining building permits
- Can dispute tax assessments through contentieux process
- Anonymous voting rights in budget allocation

---

### 3. **Municipal Agent Dashboard**
📁 File: `frontend/dashboards/agent/index.html`

**Purpose:** Field verification and public service complaint management

**Key Functions:**
- **Address Verification:** Uses Nominatim API to validate declared addresses
  - Free API integration with fallback suggestions
  - Returns GPS coordinates for satellite verification
- **Property/Land Verification:** Mark declarations as VERIFIED/INCORRECT/PARTIAL
- **Service Complaint Management:**
  - Receive assigned complaints (7 types: lighting, drainage, roads, etc.)
  - Assign complaints to self
  - Update complaint status and resolution
  - Track resolution details

**Workflow:**
1. Address submitted → Nominatim geocoding → Verification result
2. Property declared → Agent validates against satellite/ground truth
3. Citizen submits complaint → Agent assigns and resolves

---

### 4. **Inspector Dashboard**
📁 File: `frontend/dashboards/inspector/index.html`

**Purpose:** Field verification with satellite imagery integration

**Key Functions:**
- **Items to Inspect:**
  - Properties awaiting satellite verification
  - Lands awaiting field inspection
- **Inspection Reports:**
  - Submit findings (verified/discrepancies)
  - Upload evidence URLs (photos, measurements)
  - Satellite verification flagging
  - Inspector recommendations
- **Satellite Imagery Access:**
  - NASA GIBS (daily updates)
  - USGS Landsat (monthly, high-resolution)
  - OpenStreetMap tiles (aerial reference)
  - Free API access, no authentication required

**Workflow:**
1. Property declared → Inspector notified
2. Inspector pulls satellite imagery from free sources
3. Submits report with findings (verified/not verified/discrepancies)
4. Discrepancies flag for agent follow-up

---

### 5. **Finance Officer Dashboard**
📁 File: `frontend/dashboards/finance/index.html`

**Purpose:** Tax collection and revenue management

**Key Responsibilities (Receveur des Finances):**
- **Tax Debtor Management:**
  - List users with unpaid taxes (sorted by amount)
  - Contact debtors for payment reminders
  - Track outstanding amounts
- **Payment Attestations:**
  - Issue certificates proving all taxes are paid
  - Required for Article 13 (permit requests)
  - Blocks if any unpaid taxes exist
- **Payment Receipts:**
  - User payment history
  - Payment reference tracking
  - Total amount collection verification
- **Revenue Reports:**
  - Monthly/yearly revenue breakdown
  - Payment count metrics
  - Delinquency analysis

**Article 13 Enforcement:**
- Verifies tax payment before permit approval
- Provides attestation documents to citizens/businesses
- Tracks non-compliance cases

---

### 6. **Urbanism Officer Dashboard**
📁 File: `frontend/dashboards/urbanism/index.html`

**Purpose:** Building permit approval and Article 13 enforcement

**Key Functions:**
- **Permit Review:**
  - View pending permit requests
  - Check tax payment status for each requestor
  - Approve permits (if taxes paid)
  - Block permits (if taxes unpaid per Article 13)
- **Article 13 Enforcement:**
  - Automatic blocking of permits for users with outstanding taxes
  - Send payment reminders to blocked requestors
  - Approve once taxes are paid
- **Permit Registry:**
  - Approved permits log
  - Rejection tracking with reasons
  - Decision dates and audit trail

**Decision Options:**
- ✓ **APPROVED:** If user has no unpaid taxes
- ✗ **BLOCKED:** If user has outstanding taxes (Article 13)
- ✗ **REJECTED:** Administrative grounds

---

### 7. **Contentieux Officer Dashboard**
📁 File: `frontend/dashboards/contentieux/index.html`

**Purpose:** Tax dispute resolution and appeals (Articles 23-26)

**Key Responsibilities (Officier de Contentieux):**

**Article 23 - Dispute Submission:**
- Receive citizen/business tax dispute claims
- Document claimed amounts and justifications
- Store supporting evidence

**Articles 24-25 - Commission Review:**
- Submit disputes to Commission de Révision
- Commission evaluates:
  - Validity of claimed amount
  - Calculation accuracy
  - Supporting documentation
  - Applicable law
- Commission decision options:
  - ACCEPT: Reduce tax to claimed amount
  - REJECT: Maintain original tax
  - PARTIAL: Adjust to recommended amount

**Article 26 - Final Decision:**
- Issue binding final ruling
- Adjust tax amount accordingly
- May waive/reduce penalties
- Allow appeal escalation if disputed
- Maintain complete audit trail

**Workflow:**
1. Citizen submits dispute → Officer receives
2. Officer prepares for Commission review
3. Commission provides recommendation
4. Officer issues final decision
5. If appealed → Escalate to superior court

**Dispute Status Tracking:**
- SUBMITTED (under review)
- COMMISSION_REVIEWED (Commission findings received)
- DECIDED (final ruling issued)
- APPEALED (escalated if disputed)

---

### 8. **Admin Dashboard**
📁 File: `frontend/dashboards/admin/index.html`

**Purpose:** System administration and user management

**Key Functions:**
- **User Management:**
  - Create municipal staff (agents, inspectors, officers)
  - List all users with pagination
  - Get user details and profiles
  - Update user information
  - Deactivate users (soft delete)
- **System Statistics:**
  - User counts by role (8 roles)
  - Tax metrics (total, paid, pending)
  - Revenue collected
  - Payment count tracking
- **System Status:**
  - API health check
  - Database connectivity verification

**Admin-Only Operations:**
- Cannot create citizen/business accounts (self-registration only)
- Can create: agents, inspectors, finance officers, contentieux officers, urbanism officers, other admins
- View all system data without restrictions
- Generate system reports

---

## Technical Integration Points

### Authentication
All dashboards require:
- Valid JWT access token (stored in localStorage)
- Token header: `Authorization: Bearer {token}`
- Automatic redirect to login if token missing/expired

### API Endpoints Used by Each Dashboard

**Citizen:**
- `/api/auth/me` - Current user info
- `/api/tib/properties` - Property management
- `/api/ttnb/lands` - Land management
- `/api/payments/my-payments` - Payment history
- `/api/disputes/` - Dispute management
- `/api/permits/my-requests` - Permit requests
- `/api/reclamations/my-reclamations` - Complaints
- `/api/budget/projects` - Budget voting

**Business:** (Similar to Citizen, TTNB-focused)
- `/api/ttnb/lands` - Land declarations
- `/api/ttnb/my-taxes` - Tax summary
- `/api/payments/my-payments` - Payment tracking
- `/api/permits/request` - Permit requests
- `/api/disputes/` - Dispute submission

**Municipal Agent:**
- `/api/agent/verify/address` - Address geocoding
- `/api/agent/verify/property/{id}` - Property verification
- `/api/agent/verify/land/{id}` - Land verification
- `/api/agent/reclamations` - Assigned complaints
- `/api/reclamations/all` - All complaints

**Inspector:**
- `/api/inspector/properties/to-inspect` - Properties awaiting inspection
- `/api/inspector/lands/to-inspect` - Lands awaiting inspection
- `/api/inspector/report` - Submit inspection report
- `/api/inspector/property/{id}/satellite-imagery` - Get satellite sources
- `/api/inspector/my-reports` - Inspection history

**Finance Officer:**
- `/api/finance/debtors` - Tax debtors list
- `/api/finance/attestation/{user_id}` - Issue attestation
- `/api/finance/payment-receipts/{user_id}` - Payment history
- `/api/finance/revenue-report` - Revenue analysis

**Urbanism Officer:**
- `/api/permits/pending` - Pending permit requests
- `/api/permits/{id}/decide` - Approve/reject permits

**Contentieux Officer:**
- `/api/disputes/` - List disputes
- `/api/disputes/{id}/commission-review` - Submit to Commission
- `/api/disputes/{id}/decision` - Issue final decision

**Admin:**
- `/api/admin/users` - User management
- `/api/admin/stats` - System statistics

---

## Customization & Extension

### Adding a New Field to a Dashboard

1. Update the HTML form in the dashboard file
2. Update the form submission handler (JavaScript function)
3. Create/update the corresponding API endpoint in the backend
4. Test via Insomnia collection

### Adding a New Dashboard Section

1. Create a new `<div id="section-name" class="section">` block
2. Add navigation link in sidebar: `<a class="nav-link" onclick="showSection('section-name')">Label</a>`
3. Add load function: `async function loadSectionData() { ... }`
4. Call function from section display: `if (sectionId === 'section-name') loadSectionData();`

### Styling Customization

All dashboards share consistent styling:
- **Primary Color:** Purple gradient `#667eea → #764ba2`
- **Borders:** Light gray with subtle shadows
- **Typography:** Segoe UI, 14px base
- **Card Width:** 95% with 2rem padding
- **Responsive:** Grid-based (sidebar + content)

Modify the `<style>` section to customize colors, fonts, or layout.

---

## Database Integration

### TIB (Taxe sur les Immeubles Bâtis)
- **Declaration:** Citizens declare property details
- **Calculation:** Surface × Service Rate = Annual Tax
- **Penalties:** Article 19 applied for late declaration/payment
- **Verification:** Inspector confirms satellite data

### TTNB (Taxe sur les Terrains Non Bâtis)
- **Declaration:** Businesses declare land parcels
- **Calculation:** 0.3% × Vénale Value = Annual Tax
- **Exemptions:** Article 32-33 exemptions applied
- **Updates:** Annual recalculation based on property value

### Dispute Workflow (Articles 23-26)
- **Submission:** Citizen claims tax is incorrect (Article 23)
- **Commission:** Officer submits to Commission de Révision (Article 24)
- **Review:** Commission evaluates and recommends (Article 25)
- **Decision:** Officer issues final ruling (Article 26)
- **Appeal:** If disputed, escalate to court

### Permit Enforcement (Article 13)
- **Requirement:** All taxes must be paid before permit approval
- **Check:** Urbanism Officer verifies via Finance Officer
- **Block:** Automatic rejection if unpaid taxes > 0
- **Unblock:** Approve after payment confirmation

---

## Error Handling

All dashboards implement:
- **API Error Messages:** Display error from backend
- **Form Validation:** Required fields checked before submit
- **Network Errors:** Graceful fallback with retry option
- **Token Expiration:** Automatic redirect to login

### Common Error Messages

| Error | Cause | Resolution |
|-------|-------|-----------|
| 401 Unauthorized | Token expired | Re-login |
| 403 Forbidden | Insufficient permissions | Check user role |
| 400 Bad Request | Invalid form data | Verify all fields |
| 404 Not Found | Resource doesn't exist | Check ID correctness |
| 500 Server Error | Backend issue | Contact admin |

---

## Testing Each Dashboard

### Using Insomnia Collection

1. Open `tests/insomnia_collection.json` in Insomnia
2. Create environment with base URL: `http://localhost:3000`
3. Register a test user (citizen/business)
4. Login to get JWT token
5. Copy token to environment variable
6. Navigate to corresponding dashboard
7. Execute actions and verify API responses

### Manual Testing Checklist

**For Each Dashboard:**
- [ ] Login redirects to correct role dashboard
- [ ] Navigation links load appropriate sections
- [ ] Forms submit without errors
- [ ] Tables populate with API data
- [ ] Action buttons (approve, reject, etc.) work
- [ ] Logout clears token and redirects
- [ ] Responsive design on mobile
- [ ] Error messages display properly

---

## Performance Considerations

### Optimization Techniques

1. **Lazy Loading:** Data loads when section accessed
2. **Caching:** Store previously fetched data in variables
3. **Pagination:** Large tables paginated in backend
4. **Rate Limiting:** Nominatim API limits to ~1 req/sec (handled in backend)

### API Response Times

- Auth endpoints: < 100ms
- Tax calculations: < 200ms
- Satellite imagery: < 500ms (free API may vary)
- Database queries: < 300ms

---

## Security Best Practices

1. **JWT Tokens:**
   - Never store in plain text
   - Use secure HTTP cookies (production)
   - Set expiration times (1hr access, 30 days refresh)
   - Revoke on logout (blacklist)

2. **API Calls:**
   - Always include Authorization header
   - Validate all inputs on frontend
   - Use HTTPS in production

3. **Role-Based Access:**
   - Backend enforces role checks
   - Frontend shows role-appropriate sections
   - Cannot bypass client-side restrictions

4. **Sensitive Data:**
   - Never log tokens or passwords
   - Clear token on logout
   - Use POST for data submission (not GET)

---

## Troubleshooting

### Dashboard Won't Load
1. Check browser console for errors (F12)
2. Verify API is running: `curl http://localhost:5000/health`
3. Confirm token is valid: Check localStorage
4. Clear browser cache: Ctrl+Shift+Delete

### API Calls Fail (CORS Error)
1. Verify backend has CORS enabled
2. Check nginx reverse proxy configuration
3. Use proper content-type header

### Satellite Imagery Not Loading
1. Free APIs may have rate limits
2. Check internet connection
3. Verify coordinates are valid
4. Use alternative source (OSM tiles)

### Payments Not Recording
1. Verify Finance Officer has permissions
2. Check payment method is valid
3. Confirm user has pending taxes
4. Review backend logs

---

## Contact & Support

For issues or questions about the dashboards:
1. Check README.md for general setup
2. Review API endpoint documentation
3. Check Insomnia collection for example requests
4. Contact system administrator

---

**Version:** 1.0  
**Last Updated:** 2025  
**Status:** Production Ready
