#!/usr/bin/env python
"""
Seed script for TUNAX database
Loads communes from CSV and initializes municipal configurations
Supports Code de la Fiscalité Locale 2025 legal framework
"""
import csv
import sys
import os
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from extensions.db import db
from models import (
    Commune, MunicipalReferencePrice, MunicipalServiceConfig,
    User, UserRole
)

# Legal TIB Category Bounds (Code de la Fiscalité Locale 2025)
TIB_LEGAL_BOUNDS = {
    1: {'name': 'Category 1 (≤100m²)', 'min': 100, 'max': 178},
    2: {'name': 'Category 2 (100-200m²)', 'min': 163, 'max': 238},
    3: {'name': 'Category 3 (200-400m²)', 'min': 217, 'max': 297},
    4: {'name': 'Category 4 (>400m²)', 'min': 271, 'max': 356},
}

# Default services (Article 5 - Code de la Fiscalité Locale)
DEFAULT_SERVICES = [
    {'name': 'Collecte des ordures ménagères', 'code': 'SVC001'},
    {'name': 'Entretien des voiries', 'code': 'SVC002'},
    {'name': 'Éclairage public', 'code': 'SVC003'},
    {'name': 'Assainissement', 'code': 'SVC004'},
    {'name': 'Espaces verts', 'code': 'SVC005'},
]

def seed_communes():
    """Load communes from CSV file"""
    csv_path = os.path.join(os.path.dirname(__file__), 'seed_data', 'communes_tn.csv')
    
    if not os.path.exists(csv_path):
        print(f"ERROR: CSV file not found at {csv_path}")
        return 0
    
    created_count = 0
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Check if commune already exists
            existing = Commune.query.filter_by(
                code_municipalite=row['code_municipalite']
            ).first()
            
            if existing:
                print(f"  Skipping {row['nom_municipalite_fr']} (already exists)")
                continue
            
            commune = Commune(
                code_municipalite=row['code_municipalite'],
                nom_municipalite_fr=row['nom_municipalite_fr'],
                code_gouvernorat=row['code_gouvernorat'],
                nom_gouvernorat_fr=row['nom_gouvernorat_fr'],
                type_mun_fr=row['type_mun_fr']
            )
            db.session.add(commune)
            created_count += 1
    
    db.session.commit()
    return created_count

def seed_reference_prices(commune_id):
    """Initialize reference prices for a commune (legal bounds per Code)"""
    created_count = 0
    
    for category, bounds in TIB_LEGAL_BOUNDS.items():
        # Check if already exists
        existing = MunicipalReferencePrice.query.filter_by(
            commune_id=commune_id,
            tib_category=category
        ).first()
        
        if existing:
            continue
        
        # Set middle value of legal range
        reference_price = (bounds['min'] + bounds['max']) / 2
        
        ref_price = MunicipalReferencePrice(
            commune_id=commune_id,
            tib_category=category,
            legal_min=bounds['min'],
            legal_max=bounds['max'],
            reference_price_per_m2=reference_price,
            set_by_user_id=None,  # Will be set by MINISTRY_ADMIN initially
            set_at=datetime.utcnow()
        )
        db.session.add(ref_price)
        created_count += 1
    
    db.session.commit()
    return created_count

def seed_services(commune_id):
    """Initialize default services for a commune"""
    created_count = 0
    
    for service in DEFAULT_SERVICES:
        # Check if already exists
        existing = MunicipalServiceConfig.query.filter_by(
            commune_id=commune_id,
            service_code=service['code'],
            locality_name=None
        ).first()
        
        if existing:
            continue
        
        svc = MunicipalServiceConfig(
            commune_id=commune_id,
            locality_name=None,
            service_name=service['name'],
            service_code=service['code'],
            is_available=True,
            configured_at=datetime.utcnow()
        )
        db.session.add(svc)
        created_count += 1
    
    db.session.commit()
    return created_count

def seed_ministry_admin():
    """Create initial MINISTRY_ADMIN user for system initialization"""
    # Check if ministry admin already exists
    existing = User.query.filter_by(role=UserRole.MINISTRY_ADMIN).first()
    if existing:
        print("  Skipping MINISTRY_ADMIN (already exists)")
        return 0
    
    admin = User(
        username='ministry_admin',
        email='admin@ministry.tn',
        first_name='Ministry',
        last_name='Administrator',
        role=UserRole.MINISTRY_ADMIN,
        commune_id=None,  # Ministry admin has no commune
        is_active=True
    )
    admin.set_password('change-me-in-production')
    
    db.session.add(admin)
    db.session.commit()
    
    print("  Created MINISTRY_ADMIN user (username: ministry_admin)")
    print("    ⚠️  WARNING: Change default password immediately in production!")
    
    return 1

def main():
    """Main seed function"""
    app = create_app()
    
    with app.app_context():
        print("\n" + "="*70)
        print("TUNAX Database Seed Script")
        print("Loading Tunisian municipalities and initializing configurations")
        print("="*70 + "\n")
        
        try:
            # 1. Seed communes
            print("1️⃣  Loading communes from CSV...")
            commune_count = seed_communes()
            print(f"   ✅ Loaded/found {commune_count} communes\n")
            
            # 2. Initialize reference prices and services for all communes
            print("2️⃣  Initializing reference prices and services for each commune...")
            communes = Commune.query.all()
            total_prices = 0
            total_services = 0
            
            for commune in communes:
                prices = seed_reference_prices(commune.id)
                services = seed_services(commune.id)
                total_prices += prices
                total_services += services
                if prices > 0 or services > 0:
                    print(f"   - {commune.nom_municipalite_fr}: {prices} price categories, {services} services")
            
            print(f"   ✅ Initialized {total_prices} reference price configurations")
            print(f"   ✅ Initialized {total_services} service configurations\n")
            
            # 3. Create MINISTRY_ADMIN user
            print("3️⃣  Creating MINISTRY_ADMIN user...")
            admin_count = seed_ministry_admin()
            print(f"   ✅ Created {admin_count} administrator account\n")
            
            print("="*70)
            print("✅ Database seeding completed successfully!")
            print("="*70)
            print("\nNext steps:")
            print("1. Log in with MINISTRY_ADMIN account to verify system")
            print("2. Review and adjust reference prices per municipality if needed")
            print("3. Activate/deactivate services per municipality")
            print("4. Create MUNICIPAL_ADMIN users for each commune via /api/ministry/municipal-admins")
            print("5. Review legal compliance in Code de la Fiscalité Locale 2025\n")
            
            return 0
            
        except Exception as e:
            print(f"\n❌ Error during seeding: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc()
            db.session.rollback()
            return 1

if __name__ == '__main__':
    sys.exit(main())
