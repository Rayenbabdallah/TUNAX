# TUNAX Docker Setup & Quick Start Guide

This guide walks you through running TUNAX using Docker and seeding the database with demo users.

## Prerequisites

- Docker & Docker Compose installed
- Git (to clone the repository)

## Quick Start (5 minutes)

# All-in-one commands (copy/paste):
cd docker
docker-compose down -v
docker-compose up -d
docker-compose exec backend python -c "from alembic.config import Config; from alembic import command; alembic_cfg = Config('migrations/alembic.ini'); command.upgrade(alembic_cfg, 'head')"
docker-compose exec backend python seed_communes.py
docker-compose exec backend python seed_demo.py

# Verify
curl http://localhost:5000/health
docker-compose ps

### 1. Navigate to Project Root

```bash
cd c:\Users\rayen\Desktop\TUNAX
```

### 2. Start Services with Docker Compose

```bash
cd docker
docker-compose up -d
```

This starts:
- **PostgreSQL** database (port 5432)
- **Redis** cache (port 6379)
- **TUNAX Backend** API (port 5000)

### 3. Run Database Migrations

```bash
# From the docker directory
docker-compose exec backend python -c "from alembic.config import Config; from alembic import command; alembic_cfg = Config('migrations/alembic.ini'); command.upgrade(alembic_cfg, 'head')"
```

This applies all database migrations:
- Initial schema (users, properties, taxes, payments, etc.)
- Document workflow tables
- Two-factor authentication tables

### 4. Seed Communes (Municipalities)

```bash
docker-compose exec backend python seed_communes.py
```

This initializes:
- 98 Tunisian municipalities (communes)
- Reference prices for 392 configurations
- 490 service configurations
- Creates MINISTRY_ADMIN user (default password: `TunaxDemo123!`)

**⚠️ Important:** Communes must be seeded BEFORE demo users!

### 5. Seed Demo Users

```bash
docker-compose exec backend python seed_demo.py
```

This creates 9 demo users with different roles (all password: `TunaxDemo123!`):

| Username | Email | Role | Password | 2FA Enabled |
|----------|-------|------|----------|-------------|
| demo_citizen | citizen.demo@tunax.tn | CITIZEN | TunaxDemo123! | ❌ |
| demo_business | business.demo@tunax.tn | BUSINESS | TunaxDemo123! | ❌ |
| demo_agent | agent.demo@tunax.tn | MUNICIPAL_AGENT | TunaxDemo123! | ❌ |
| demo_inspector | inspector.demo@tunax.tn | INSPECTOR | TunaxDemo123! | ❌ |
| demo_finance | finance.demo@tunax.tn | FINANCE_OFFICER | TunaxDemo123! | ❌ |
| demo_contentieux | contentieux.demo@tunax.tn | CONTENTIEUX_OFFICER | TunaxDemo123! | ❌ |
| demo_urbanism | urbanism.demo@tunax.tn | URBANISM_OFFICER | TunaxDemo123! | ❌ |
| demo_admin | admin.demo@tunax.tn | ADMIN | TunaxDemo123! | ❌ |
| ministry_admin | ministry@tunax.tn | ADMIN (Ministry) | TunaxDemo123! | ❌ |

**Note:** All 2FA is disabled by default. You can enable it via the dashboard UI or Insomnia API.

### 6. Verify API is Running

```bash
curl http://localhost:5000/
```

Expected response:
```json
{
  "message": "TUNAX API v2.0 - Tunisian Tax Management System",
  "version": "2.0.0",
  "status": "operational"
}
```

## Testing with Insomnia

1. Import the collection: `tests/TUNAX_Insomnia_Collection.json`
2. Set environment variables:
   - `base_url`: `http://localhost:5000`
3. Test authentication:
   - **No 2FA:** Use `demo_citizen` credentials
   - **With 2FA:** Use `demo_admin` credentials, follow 2FA flow

### 2FA Testing Flow

1. **Login** with `demo_admin` → Get `temp_token` and `requires_2fa: true`
2. Generate TOTP code using the secret from seed output (use Google Authenticator or similar)
3. **Verify 2FA Login** with `temp_token` and 6-digit code → Get `access_token`

## Local Development (Without Docker)

### 1. Setup Python Environment

```bash
cd backend
python -m venv venv
venv\Scripts\activate  # Windows
pip install -r requirements.txt
```

### 2. Configure Environment

Create `backend/.env`:
```env
FLASK_ENV=development
DATABASE_URL=sqlite:///c:/Users/rayen/Desktop/TUNAX/backend/tunax.db
JWT_SECRET_KEY=your-super-secret-jwt-key-here-change-in-production
UPLOAD_FOLDER=c:/Users/rayen/Desktop/TUNAX/backend/uploads
```

### 3. Run Migrations & Seed

```bash
alembic upgrade head
python seed_demo.py
```

### 4. Start Backend

```bash
python app.py
```

### 5. Open Frontend

Open `frontend/common_login/index.html` in a browser, or use the role-specific dashboards in `frontend/dashboards/`.

## Database Management

### View Logs

```bash
docker-compose logs -f backend
```

### Access Database Shell

```bash
docker-compose exec db psql -U tunax -d tunax_db
```

### Reset Database (Fresh Start)

```bash
docker-compose down -v  # Remove volumes
docker-compose up -d
docker-compose exec backend python -c "from alembic.config import Config; from alembic import command; alembic_cfg = Config('migrations/alembic.ini'); command.upgrade(alembic_cfg, 'head')"
docker-compose exec backend python seed_communes.py
docker-compose exec backend python seed_demo.py
```

**Correct Order:** migrations → communes → demo users

## Complete Fresh Start Workflow (Copy & Paste Ready)

```bash
# Navigate to docker directory
cd docker

# Step 1: Remove everything
docker-compose down -v

# Step 2: Start fresh containers
docker-compose up -d

# Wait for PostgreSQL to be ready (10-15 seconds)
sleep 15

# Step 3: Run migrations
docker-compose exec backend python -c "from alembic.config import Config; from alembic import command; alembic_cfg = Config('migrations/alembic.ini'); command.upgrade(alembic_cfg, 'head')"

# Step 4: Seed communes (MUST be before demo users!)
docker-compose exec backend python seed_communes.py

# Step 5: Seed demo users
docker-compose exec backend python seed_demo.py

# Step 6: Verify everything is running
curl http://localhost:5000/
docker-compose ps
```

**Expected Output:**
```
✅ Migrations: 3 successful (initial, document workflow, 2FA)
✅ Communes: 98 loaded with 392 price configs & 490 service configs
✅ Demo Users: 9 created (+ ministry_admin from communes)
✅ API: Healthy and operational
```

**Time:** ~2-3 minutes total

## Production Deployment

### Security Checklist

- [ ] Change `JWT_SECRET_KEY` to a strong random value (32+ characters)
- [ ] Update database credentials in `docker-compose.yml`
- [ ] Enable HTTPS (configure nginx SSL certificates)
- [ ] Review rate limiting settings in `app.py`
- [ ] Configure email service for notifications
- [ ] Set up regular database backups
- [ ] Review log retention policy (`logs/tunax.log`)

### Environment Variables

```env
FLASK_ENV=production
DATABASE_URL=postgresql://user:pass@db:5432/tunax_prod
JWT_SECRET_KEY=<generate-with-secrets-token-hex-32>
REDIS_URL=redis://redis:6379/0
UPLOAD_FOLDER=/app/uploads
MAX_CONTENT_LENGTH=16777216  # 16MB file upload limit
```

### Generate Secure JWT Secret

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

## Troubleshooting

### Port Already in Use

```bash
# Check what's using port 5000
netstat -ano | findstr :5000

# Kill the process or change port in docker-compose.yml
```

### Database Connection Errors

```bash
# Verify database is running
docker-compose ps

# Check logs
docker-compose logs db
```

### Migration Errors

```bash
# Rollback one migration
docker-compose exec backend alembic -c migrations/alembic.ini downgrade -1

# View migration history
docker-compose exec backend alembic -c migrations/alembic.ini history
```

### 2FA Not Working

- Verify time synchronization on server (TOTP is time-based)
- Check secret key from seed output matches authenticator app
- Try using a backup code instead

## API Documentation

Once running, OpenAPI docs available at:
- **Swagger UI:** http://localhost:5000/swagger-ui
- **ReDoc:** http://localhost:5000/redoc

## Support

For issues or questions:
- Check logs: `docker-compose logs -f backend`
- Review API errors in Insomnia response
- Verify JWT token is valid (not expired)

## Key Features

✅ **JWT Authentication** with role-based access control  
✅ **Two-Factor Authentication (2FA)** for sensitive roles  
✅ **Rate Limiting** (100 requests/hour default, 5/min login)  
✅ **PDF Receipt Generation** for payments  
✅ **Payment Plans** with installment tracking  
✅ **Budget Voting** with citizen participation  
✅ **Document Upload** with workflow tracking  
✅ **Dispute Management** for tax contestation  
✅ **Permit System** with eligibility checks  
✅ **Audit Logging** for all critical operations  

---

**Ready to Go!** 🚀 Your TUNAX instance is now running. Login with demo credentials and explore the API.
