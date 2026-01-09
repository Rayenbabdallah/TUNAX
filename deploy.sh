#!/bin/bash
# TUNAX System - Quick Start Deployment Script
# This script automates the complete setup and deployment of the TUNAX system

set -e

echo "╔════════════════════════════════════════════════════════════════╗"
echo "║          TUNAX - Municipal Tax Management System               ║"
echo "║         Tunisian Municipal Tax Code Implementation             ║"
echo "╚════════════════════════════════════════════════════════════════╝"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
BACKEND_PORT=5000
FRONTEND_PORT=3000
DB_PORT=5432
PROJECT_ROOT=$(pwd)

echo -e "\n${YELLOW}Step 1: Verifying Prerequisites${NC}"
echo "================================"

# Check Docker
if ! command -v docker &> /dev/null; then
    echo -e "${RED}✗ Docker is not installed${NC}"
    echo "Install Docker from: https://www.docker.com/products/docker-desktop"
    exit 1
fi
echo -e "${GREEN}✓ Docker found$(docker --version)${NC}"

# Check Docker Compose
if ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}✗ Docker Compose is not installed${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Docker Compose found$(docker-compose --version)${NC}"

# Create .env file if not exists
if [ ! -f "backend/.env" ]; then
    echo -e "\n${YELLOW}Step 2: Configuring Environment${NC}"
    echo "================================"
    
    echo "Creating backend/.env file..."
    cp backend/.env.example backend/.env 2>/dev/null || cat > backend/.env << EOF
DATABASE_URL=postgresql://tunax_user:tunax_password@localhost:5432/tunax_db
JWT_SECRET_KEY=$(openssl rand -hex 32)
JWT_ACCESS_TOKEN_EXPIRES=3600
JWT_REFRESH_TOKEN_EXPIRES=2592000
FLASK_ENV=production
FLASK_DEBUG=False
FLASK_APP=app.py
API_TITLE=Tunisian Municipal Tax Management System
API_VERSION=v1
NOMINATIM_TIMEOUT=10
MAX_CONTENT_LENGTH=16777216
UPLOAD_FOLDER=./uploads
EOF
    
    echo -e "${GREEN}✓ Environment file created${NC}"
    echo "  Note: Change JWT_SECRET_KEY in production!"
else
    echo -e "${GREEN}✓ Environment file already exists${NC}"
fi

echo -e "\n${YELLOW}Step 3: Building Docker Images${NC}"
echo "================================"

cd docker

# Build images
echo "Building PostgreSQL + Backend + Frontend images..."
docker-compose build --no-cache

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Images built successfully${NC}"
else
    echo -e "${RED}✗ Image build failed${NC}"
    exit 1
fi

echo -e "\n${YELLOW}Step 4: Starting Services${NC}"
echo "================================"

echo "Starting TUNAX services (PostgreSQL, Backend, Frontend)..."
docker-compose up -d

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Services started${NC}"
else
    echo -e "${RED}✗ Services failed to start${NC}"
    docker-compose logs
    exit 1
fi

# Wait for services to be ready
echo -e "\n${YELLOW}Waiting for services to be ready...${NC}"
sleep 10

echo -e "\n${YELLOW}Step 5: Verifying Services${NC}"
echo "================================"

# Check Backend
echo -n "Checking Backend API..."
if curl -s http://localhost:$BACKEND_PORT/health > /dev/null; then
    echo -e "${GREEN} ✓ Running${NC}"
else
    echo -e "${RED} ✗ Not responding${NC}"
fi

# Check Frontend
echo -n "Checking Frontend..."
if curl -s http://localhost:$FRONTEND_PORT/ > /dev/null; then
    echo -e "${GREEN} ✓ Running${NC}"
else
    echo -e "${RED} ✗ Not responding${NC}"
fi

# Check Database
echo -n "Checking Database..."
docker-compose exec -T postgres pg_isready -U tunax_user -d tunax_db 2>/dev/null
if [ $? -eq 0 ]; then
    echo -e "${GREEN} ✓ Ready${NC}"
else
    echo -e "${RED} ✗ Not ready${NC}"
fi

echo -e "\n${GREEN}╔═══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║              ✓ TUNAX System Successfully Started!             ║${NC}"
echo -e "${GREEN}╚═══════════════════════════════════════════════════════════════╝${NC}"

echo -e "\n${YELLOW}Quick Start Guide:${NC}"
echo "=================="
echo ""
echo "1. ${GREEN}Access the Application:${NC}"
echo "   - Login Page:     http://localhost:$FRONTEND_PORT/common_login/index.html"
echo "   - API Docs:       http://localhost:$BACKEND_PORT/api/docs"
echo ""
echo "2. ${GREEN}Default Test User:${NC}"
echo "   - Register a new citizen or business account at the login page"
echo "   - All features are available immediately after login"
echo ""
echo "3. ${GREEN}Create Admin/Staff Users:${NC}"
echo "   - Login as Admin (create one via registration, then promote in database)"
echo "   - Use Admin Dashboard to create:"
echo "     • Municipal Agents (address verification, complaints)"
echo "     • Inspectors (satellite verification)"
echo "     • Finance Officers (tax collection, attestations)"
echo "     • Contentieux Officers (dispute resolution)"
echo "     • Urbanism Officers (permit approval)"
echo ""
echo "4. ${GREEN}Tax Declarations:${NC}"
echo "   - TIB (Built Properties):    Citizen Dashboard → Properties"
echo "   - TTNB (Non-Built Land):     Business Dashboard → TTNB Declarations"
echo ""
echo "5. ${GREEN}Dispute Resolution (Articles 23-26):${NC}"
echo "   - Submit:     Citizen/Business → Disputes section"
echo "   - Review:     Contentieux → Commission de Révision"
echo "   - Decide:     Contentieux → Final Decisions"
echo ""
echo "6. ${GREEN}Permits (Article 13):${NC}"
echo "   - Request:    Citizen/Business → Permits section"
echo "   - Verify:     Urbanism Officer checks tax payment status"
echo "   - Block:      Automatic if unpaid taxes > 0"
echo ""
echo "7. ${GREEN}Testing with Insomnia:${NC}"
echo "   - Import: tests/insomnia_collection.json"
echo "   - Run 35+ API endpoint tests"
echo ""
echo "8. ${GREEN}Monitoring Logs:${NC}"
echo "   - Backend:    docker-compose logs backend"
echo "   - Database:   docker-compose logs postgres"
echo "   - Frontend:   docker-compose logs frontend"
echo ""
echo "${YELLOW}Useful Commands:${NC}"
echo "================="
echo "  Stop services:     docker-compose down"
echo "  Restart services:  docker-compose restart"
echo "  View logs:         docker-compose logs -f"
echo "  Database shell:    docker-compose exec postgres psql -U tunax_user -d tunax_db"
echo ""
echo "${YELLOW}Documentation:${NC}"
echo "==============="
echo "  README.md:              Complete setup and API documentation"
echo "  frontend/DASHBOARD_GUIDE.md: User dashboard guide (8 roles)"
echo "  tests/insomnia_collection.json: API test scenarios"
echo ""
echo "${YELLOW}Architecture:${NC}"
echo "============="
echo "  Backend:   Flask 3.0 REST API with JWT authentication"
echo "  Database:  PostgreSQL 15 with 11 relational models"
echo "  Frontend:  HTML5/CSS3/JavaScript with responsive design"
echo "  APIs:      Free geolocation (Nominatim) + satellite imagery (NASA, USGS)"
echo ""
echo -e "${GREEN}✓ System Ready for Testing!${NC}\n"

# cd back to root
cd $PROJECT_ROOT
