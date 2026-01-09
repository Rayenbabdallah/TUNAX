# TUNAX Quick Reference Guide

## 🚀 Getting Started (5 Minutes)

### 1. Start the System
```bash
cd TUNAX
chmod +x deploy.sh
./deploy.sh
```

### 2. Access the Application
- **Login Page:** http://localhost:3000/common_login/index.html
- **API Docs:** http://localhost:5000/api/docs
- **Health Check:** http://localhost:5000/health

### 3. Create Your First Account
1. Go to login page
2. Select "Register" tab
3. Choose "Citizen" or "Business"
4. Fill in details and submit
5. Login with new account

---

## 🔐 Default Admin Setup

### Create Admin User (First Time)
1. Register as a **Citizen** with username: `admin`
2. Once logged in, contact database administrator to set role to ADMIN
3. Or use SQL:
```sql
UPDATE "user" SET role = 'admin' WHERE username = 'admin';
```

### Create Staff Users (As Admin)
1. Login to Admin Dashboard
2. Go to "Create User" section
3. Fill form with staff details
4. Select role (agent, inspector, finance_officer, etc.)
5. Submit

---

## 📚 Quick Workflow Examples

### Example 1: Citizen Declares Property (TIB)
1. Login as Citizen
2. Go to "Properties" section
3. Click "Declare Property"
4. Enter: address, surface area, number of services
5. Submit → Tax auto-calculated
6. Pay tax
7. Request building permit

### Example 2: Business Declares Land (TTNB)
1. Login as Business
2. Go to "TTNB Declarations"
3. Enter: location, area, vénale value
4. Submit → 0.3% tax calculated
5. Pay tax
6. Request permit for construction

### Example 3: Dispute a Tax (Articles 23-26)
1. Go to "Disputes" section
2. Click "Submit Dispute"
3. Enter: tax ID, claimed amount, reason
4. Submit
5. Contentieux Officer reviews
6. Commission makes recommendation
7. Final decision issued

### Example 4: Inspector Verifies Property
1. Login as Inspector
2. Go to "Properties to Inspect"
3. Review satellite imagery
4. Submit inspection report
5. Mark as verified or flag discrepancies

---

## 🎯 Key Endpoints by Role

### Citizen
```
GET    /api/auth/me                          # Your profile
POST   /api/tib/properties                   # Declare property
GET    /api/tib/properties                   # List properties
GET    /api/tib/my-taxes                     # Tax summary
POST   /api/payments/pay                     # Pay tax
POST   /api/permits/request                  # Request permit
POST   /api/disputes/                        # Submit dispute
POST   /api/reclamations/                    # File complaint
POST   /api/budget/projects/{id}/vote        # Vote on budget
```

### Business (Similar to Citizen, TTNB-focused)
```
POST   /api/ttnb/lands                       # Declare land
GET    /api/ttnb/lands                       # List lands
GET    /api/ttnb/my-taxes                    # Tax summary (0.3%)
POST   /api/payments/pay                     # Pay tax
POST   /api/permits/request                  # Request permit (Article 13)
POST   /api/disputes/                        # Dispute tax
```

### Inspector
```
GET    /api/inspector/properties/to-inspect  # Properties awaiting verification
POST   /api/inspector/report                 # Submit inspection report
GET    /api/inspector/property/{id}/satellite-imagery  # Get satellite sources
```

### Finance Officer
```
GET    /api/finance/debtors                  # Users with unpaid taxes
POST   /api/finance/attestation/{user_id}   # Issue payment attestation
GET    /api/finance/payment-receipts/{user_id}  # User payment history
GET    /api/finance/revenue-report           # Revenue breakdown
```

### Contentieux Officer
```
GET    /api/disputes/                        # List disputes
PATCH  /api/disputes/{id}/assign            # Assign to self
PATCH  /api/disputes/{id}/commission-review # Submit to Commission
PATCH  /api/disputes/{id}/decision          # Issue final decision
```

### Urbanism Officer
```
GET    /api/permits/pending                  # Pending permit requests
PATCH  /api/permits/{id}/decide             # Approve/reject/block
```

### Admin
```
POST   /api/admin/users                      # Create staff user
GET    /api/admin/users                      # List all users
PATCH  /api/admin/users/{id}                # Update user
GET    /api/admin/stats                      # System statistics
```

---

## 🔍 Common Tasks

### Find a Specific User
```
Admin Dashboard → User Management → List Users → Search by username
```

### Check Tax Debtors
```
Finance Dashboard → Tax Debtors → View unpaid amounts
```

### Approve a Permit
```
Urbanism Dashboard → Pending Permits → Check tax status → Approve/Block
```

### Resolve a Dispute
```
Contentieux Dashboard → Assigned Disputes → Assign to self → Submit to Commission → Issue decision
```

### Verify Address
```
Agent Dashboard → Verify Address → Enter address → Get GPS coordinates
```

### Process Payment
```
Citizen/Business Dashboard → Payments → Make a Payment → Select method → Confirm
```

---

## 🐛 Troubleshooting

### Services Won't Start
```bash
docker-compose down
docker-compose up -d
docker-compose logs
```

### Can't Login
1. Check if backend is running: `curl http://localhost:5000/health`
2. Check if token is stored: `localStorage` in browser console
3. Clear cache: Ctrl+Shift+Delete

### API Returns 401 (Unauthorized)
- JWT token expired → Re-login
- Token not sent → Check Authorization header
- Invalid token format → Copy fresh token from login

### API Returns 403 (Forbidden)
- User role doesn't have permission
- Check user role in database or Admin dashboard
- Verify role decorators in backend

### Satellite Imagery Not Loading
- Free API may be temporarily down
- Check internet connection
- Try different imagery source (OSM tiles)

### Database Connection Error
```bash
docker-compose exec postgres psql -U tunax_user -d tunax_db
SELECT 1;  # Test connection
```

---

## 📊 Important SQL Queries

### Promote User to Admin
```sql
UPDATE "user" SET role = 'admin' WHERE id = 1;
```

### List All Users
```sql
SELECT id, username, email, role, is_active FROM "user";
```

### Find Unpaid Taxes
```sql
SELECT u.username, SUM(t.total_amount) as unpaid
FROM "user" u
JOIN property p ON u.id = p.owner_id
JOIN tax t ON p.id = t.property_id
WHERE t.status != 'PAID'
GROUP BY u.id;
```

### Count Properties by Status
```sql
SELECT status, COUNT(*) FROM property GROUP BY status;
```

### Recent Disputes
```sql
SELECT d.id, d.user_id, d.claimed_amount, d.status 
FROM dispute d 
ORDER BY d.created_at DESC LIMIT 10;
```

### Payment Receipts for User
```sql
SELECT * FROM payment WHERE user_id = ? ORDER BY payment_date DESC;
```

---

## 🎨 UI Navigation Quick Map

### Citizen Dashboard
```
Overview → Properties → Lands → Taxes → Payments → Disputes → Permits → Complaints → Budget
```

### Business Dashboard
```
Overview → TTNB Declarations → Tax Summary → Payments → Permits → Disputes → Budget
```

### Admin Dashboard
```
Overview → Users → Create User → Statistics → System Status
```

### Inspector Dashboard
```
Overview → To Inspect → Submit Report → My Reports → Satellite Data
```

### Finance Dashboard
```
Overview → Debtors → Attestations → Receipts → Revenue Report
```

### Agent Dashboard
```
Overview → Verify Address → Service Complaints → My Assignments → Verification Status
```

### Urbanism Dashboard
```
Overview → Pending Permits → Approved Permits → Article 13 Enforcement
```

### Contentieux Dashboard
```
Overview → Assigned Disputes → Commission Review → Final Decisions → Articles 23-26
```

---

## 📞 Support Commands

### Check System Status
```bash
curl http://localhost:5000/health
curl http://localhost:3000/
```

### View Logs
```bash
docker-compose logs -f backend        # API logs
docker-compose logs -f postgres       # Database logs
docker-compose logs -f frontend       # Nginx logs
```

### Restart Everything
```bash
docker-compose restart
```

### Stop All Services
```bash
docker-compose down
```

### Access Database Shell
```bash
docker-compose exec postgres psql -U tunax_user -d tunax_db
```

### View Environment Variables
```bash
docker-compose exec backend env | grep -i database
```

---

## 💡 Pro Tips

1. **Use Insomnia for API Testing**
   - Import: `tests/insomnia_collection.json`
   - Set environment variables
   - Run all endpoints at once

2. **Keep JWT Token Fresh**
   - Access token: 1 hour
   - Refresh token: 30 days
   - Use refresh endpoint when access expires

3. **Check Satellite Imagery**
   - Use for property verification
   - 3 free sources integrated
   - No authentication needed

4. **Tax Calculation**
   - TIB: Surface × Service Rate = Annual Tax
   - TTNB: 0.3% × Vénale Value = Annual Tax
   - Penalties: 10% late declaration + 5% late payment per month

5. **Article 13 Enforcement**
   - Permits require ALL taxes paid
   - Automatic blocking if unpaid
   - Finance Officer issues attestation

---

## 📋 Checklist for First Run

- [ ] Docker & Docker Compose installed
- [ ] Run deploy.sh successfully
- [ ] Access login page (localhost:3000)
- [ ] Register test citizen account
- [ ] Login and access citizen dashboard
- [ ] Declare a property (TIB)
- [ ] Pay the tax
- [ ] Create admin account
- [ ] Create inspector user
- [ ] Run Insomnia collection tests
- [ ] Review API documentation

---

## 📖 Documentation Files to Read

1. **First:** `README.md` (complete guide)
2. **Then:** `DASHBOARD_GUIDE.md` (UI walkthrough)
3. **Reference:** `IMPLEMENTATION_SUMMARY.md` (architecture)
4. **Details:** `FILE_INVENTORY.md` (file structure)

---

## 🎓 Learning Path

### For Developers
1. Review `app.py` structure
2. Study database models in `backend/models/`
3. Examine resource blueprints in `backend/resources/`
4. Test with Insomnia collection
5. Customize as needed

### For System Administrators
1. Run `deploy.sh` for setup
2. Create admin and staff users
3. Monitor logs and health
4. Review statistics in Admin dashboard
5. Backup database regularly

### For End Users
1. Register account (citizen/business)
2. Complete profile
3. Declare properties/lands
4. Follow workflows (pay, permit, dispute)
5. Participate in budget voting

---

## 🔗 Important URLs

| Purpose | URL |
|---------|-----|
| Login/Register | http://localhost:3000/common_login/index.html |
| API Documentation | http://localhost:5000/api/docs |
| Health Check | http://localhost:5000/health |
| Citizen Dashboard | http://localhost:3000/dashboard/citizen.html |
| Business Dashboard | http://localhost:3000/dashboard/business.html |
| Admin Dashboard | http://localhost:3000/dashboard/admin.html |
| Database (Local) | localhost:5432 |

---

## ❓ FAQ

**Q: How do I reset my password?**
A: Currently manual. Use SQL: `UPDATE user SET password = ... WHERE id = ?` (hashed with werkzeug)

**Q: Can I export data?**
A: Yes, via SQL queries or API endpoints with pagination

**Q: How do I change the language?**
A: Currently Tunisian French. Internationalization planned for v2.0

**Q: Is there a mobile app?**
A: Currently web-based. Mobile app planned for v2.0

**Q: How do I integrate a real payment gateway?**
A: Replace simulated payment in `resources/payment.py` with Stripe/PayPal API

**Q: Can I customize the tax formulas?**
A: Yes, modify `utils/calculator.py` and test in Insomnia

---

**Last Updated:** 2025  
**Status:** Production Ready  
**Version:** 1.0

For detailed information, refer to main documentation files.
