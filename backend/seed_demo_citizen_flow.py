"""Seed a complete citizen demo flow: property declaration + tax + sample document.
Run inside the backend container: python seed_demo_citizen_flow.py
"""
from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

from app import create_app
from extensions.db import db
from models.user import User
from models.property import Property, PropertyAffectation
from models.declaration import Declaration, DeclarationType
from models.tax import Tax, TaxType, TaxStatus
from models.land import Land, LandType, LandStatus
from models.payment import Payment, PaymentStatus, PaymentMethod
from models.budget import BudgetProject, BudgetProjectStatus, BudgetVote


def get_or_create_demo_citizen() -> User | None:
    user = User.query.filter_by(username="demo_citizen").first()
    return user


def seed_property_and_declaration(user: User) -> tuple[Property, Declaration]:
    # Ensure a property exists for demo citizen in commune 1
    prop = Property.query.filter_by(owner_id=user.id, street_address="1 Demo Street", city="Tunis").first()
    if not prop:
        prop = Property(
            owner_id=user.id,
            commune_id=1,
            street_address="1 Demo Street",
            city="Tunis",
            delegation="Tunis",
            post_code="1000",
            latitude=36.8065,
            longitude=10.1815,
            surface_couverte=150.0,
            surface_totale=180.0,
            affectation=PropertyAffectation.RESIDENTIAL,
            nb_floors=2,
            nb_rooms=5,
            construction_year=2015,
            reference_price_per_m2=200.0,  # within legal bounds
        )
        db.session.add(prop)
        db.session.flush()

    decl = Declaration.query.filter_by(owner_id=user.id, declaration_type=DeclarationType.PROPERTY.value, reference_id=prop.id).first()
    if not decl:
        decl = Declaration(
            owner_id=user.id,
            commune_id=prop.commune_id,
            declaration_type=DeclarationType.PROPERTY.value,
            reference_id=prop.id,
            status="submitted",
        )
        db.session.add(decl)
        db.session.flush()

    return prop, decl


def seed_tax_for_property(prop: Property) -> Tax:
    """Create a 2024 tax (payable in 2025, paid on time) and an unpaid 2025 tax (payable 2026)."""
    from utils.calculator import TaxCalculator
    
    calc = TaxCalculator.calculate_tib(prop)
    
    # 2024 tax (already payable in 2025, will be marked as PAID)
    tax_2024 = Tax.query.filter_by(property_id=prop.id, tax_year=2024, tax_type=TaxType.TIB).first()
    if not tax_2024:
        tax_2024 = Tax(
            property_id=prop.id,
            tax_type=TaxType.TIB,
            tax_year=2024,
            base_amount=float(calc.get("base_amount", 0.0)),
            rate_percent=float(calc.get("rate_percent", 0.0)),
            tax_amount=float(calc.get("tax_amount", 0.0)),
            total_amount=float(calc.get("total_amount", 0.0)),
            status=TaxStatus.CALCULATED,
        )
        db.session.add(tax_2024)
        db.session.flush()
    
    # 2025 tax (payable from 2026, still PENDING in Dec 2025)
    tax_2025 = Tax.query.filter_by(property_id=prop.id, tax_year=2025, tax_type=TaxType.TIB).first()
    if not tax_2025:
        tax_2025 = Tax(
            property_id=prop.id,
            tax_type=TaxType.TIB,
            tax_year=2025,
            base_amount=float(calc.get("base_amount", 0.0)),
            rate_percent=float(calc.get("rate_percent", 0.0)),
            tax_amount=float(calc.get("tax_amount", 0.0)),
            total_amount=float(calc.get("total_amount", 0.0)),
            status=TaxStatus.CALCULATED,  # Not yet due; no payment in 2025
        )
        db.session.add(tax_2025)
        db.session.flush()
    
    return tax_2024, tax_2025


def seed_sample_document(decl: Declaration) -> None:
    from models.document import Document, DocumentType, DocumentStatus
    # Ensure a DocumentType exists in the same commune
    dt = DocumentType.query.filter_by(commune_id=decl.commune_id, code="ID_DOCUMENT").first()
    if not dt:
        dt = DocumentType(
            commune_id=decl.commune_id,
            code="ID_DOCUMENT",
            label="ID Document",
            is_required=True,
            is_active=True,
        )
        db.session.add(dt)
        db.session.flush()

    storage_root = os.getenv("DOCUMENTS_STORAGE_PATH", "storage/documents")
    decl_dir = os.path.join(storage_root, str(decl.id))
    os.makedirs(decl_dir, exist_ok=True)
    file_path = os.path.join(decl_dir, "demo_id.pdf")
    if not os.path.exists(file_path):
        with open(file_path, "wb") as f:
            f.write(b"%PDF-1.4\n% Demo ID Document\n")

    doc = Document.query.filter_by(declaration_id=decl.id, file_name="demo_id.pdf").first()
    if not doc:
        doc = Document(
            declaration_id=decl.id,
            document_type_id=dt.id,
            uploader_id=decl.owner_id,
            storage_path=file_path,
            file_name="demo_id.pdf",
            mime_type="application/pdf",
            file_size=os.path.getsize(file_path),
            status=DocumentStatus.APPROVED,
            version=1,
        )
        db.session.add(doc)


def seed_land_and_ttnb(user: User) -> tuple[Land, Declaration, Tax]:
    # Ensure a land declaration exists for demo citizen
    land = Land.query.filter_by(owner_id=user.id, street_address="2 Demo Field", city="Tunis").first()
    if not land:
        land = Land(
            owner_id=user.id,
            commune_id=1,
            street_address="2 Demo Field",
            city="Tunis",
            delegation="Tunis",
            post_code="1000",
            latitude=36.8000,
            longitude=10.1800,
            surface=5000.0,  # 5000 m²
            land_type=LandType.BUILDABLE,
            urban_zone="faible_densite",  # Low-density zone
        )
        db.session.add(land)
        db.session.flush()

    land_decl = Declaration.query.filter_by(owner_id=user.id, declaration_type=DeclarationType.LAND.value, reference_id=land.id).first()
    if not land_decl:
        land_decl = Declaration(
            owner_id=user.id,
            commune_id=land.commune_id,
            declaration_type=DeclarationType.LAND.value,
            reference_id=land.id,
            status="submitted",
        )
        db.session.add(land_decl)
        db.session.flush()

    # Calculate TTNB for 2024 (payable in 2025, paid)
    from utils.calculator import TaxCalculator
    calc = TaxCalculator.calculate_ttnb(land)
    
    land_tax_2024 = Tax.query.filter_by(land_id=land.id, tax_year=2024, tax_type=TaxType.TTNB).first()
    if not land_tax_2024:
        land_tax_2024 = Tax(
            land_id=land.id,
            tax_type=TaxType.TTNB,
            tax_year=2024,
            base_amount=float(calc.get("base_amount", 0.0)),
            rate_percent=float(calc.get("rate_percent", 0.0)),
            tax_amount=float(calc.get("tax_amount", 0.0)),
            total_amount=float(calc.get("total_amount", 0.0)),
            status=TaxStatus.CALCULATED,
        )
        db.session.add(land_tax_2024)
        db.session.flush()
    
    # 2025 TTNB (payable from 2026, pending)
    land_tax_2025 = Tax.query.filter_by(land_id=land.id, tax_year=2025, tax_type=TaxType.TTNB).first()
    if not land_tax_2025:
        land_tax_2025 = Tax(
            land_id=land.id,
            tax_type=TaxType.TTNB,
            tax_year=2025,
            base_amount=float(calc.get("base_amount", 0.0)),
            rate_percent=float(calc.get("rate_percent", 0.0)),
            tax_amount=float(calc.get("tax_amount", 0.0)),
            total_amount=float(calc.get("total_amount", 0.0)),
            status=TaxStatus.CALCULATED,
        )
        db.session.add(land_tax_2025)
        db.session.flush()

    return land, land_decl, land_tax_2024


def seed_payment_for_citizen(user: User, tax: Tax) -> Payment:
    # Create a completed payment for the TIB tax (paid on time)
    payment = Payment.query.filter_by(user_id=user.id, tax_id=tax.id).first()
    if not payment:
        payment = Payment(
            user_id=user.id,
            tax_id=tax.id,
            amount=tax.total_amount,
            method=PaymentMethod.BANK_TRANSFER,
            status=PaymentStatus.COMPLETED,
            reference_number=f"PAY-{user.id}-{tax.id}-2025",
            attestation_issued=True,
            attestation_date=datetime.utcnow(),
            attestation_number=f"ATT-{user.id}-{tax.id}-2025",
        )
        db.session.add(payment)
        db.session.flush()
        
        # Mark tax as PAID
        tax.status = TaxStatus.PAID
    return payment


def seed_budget_projects_for_commune(commune_id: int) -> list[BudgetProject]:
    # Create sample budget projects for participatory voting
    projects = []
    sample_projects = [
        {
            "title": "Rénovation Rue de la Liberté",
            "description": "Street renovation and improvement project",
            "budget_amount": 50000.0,
        },
        {
            "title": "Parc Communal",
            "description": "Public park development and landscaping",
            "budget_amount": 75000.0,
        },
    ]
    for proj_data in sample_projects:
        existing = BudgetProject.query.filter_by(
            commune_id=commune_id,
            title=proj_data["title"]
        ).first()
        if not existing:
            proj = BudgetProject(
                commune_id=commune_id,
                title=proj_data["title"],
                description=proj_data["description"],
                budget_amount=proj_data["budget_amount"],
                status=BudgetProjectStatus.OPEN_FOR_VOTING,
            )
            db.session.add(proj)
            db.session.flush()
            projects.append(proj)
    return projects


def seed_user_votes_on_budgets(user: User, projects: list[BudgetProject]) -> None:
    # Let the citizen vote on budget projects
    for proj in projects:
        vote = BudgetVote.query.filter_by(project_id=proj.id, user_id=user.id).first()
        if not vote and proj.status == BudgetProjectStatus.OPEN_FOR_VOTING:
            vote = BudgetVote(
                project_id=proj.id,
                user_id=user.id,
                weight=1,
            )
            db.session.add(vote)
            proj.total_votes = (proj.total_votes or 0) + 1


def main() -> None:
    project_root = Path(__file__).resolve().parent.parent
    load_dotenv(project_root / ".env")
    load_dotenv(project_root / "backend" / ".env")

    app = create_app(os.getenv("FLASK_ENV", "development"))
    with app.app_context():
        user = get_or_create_demo_citizen()
        if not user:
            print("❌ demo_citizen not found. Run seed_demo.py first.")
            return
        
        # Property + TIB (2024 paid, 2025 pending)
        prop, decl = seed_property_and_declaration(user)
        tib_2024, tib_2025 = seed_tax_for_property(prop)
        seed_sample_document(decl)
        
        # Land + TTNB (2024 paid, 2025 pending)
        land, land_decl, ttnb_2024 = seed_land_and_ttnb(user)
        
        # Payments for 2024 taxes (paid on time in 2025, before 2026 due date)
        payment_tib = seed_payment_for_citizen(user, tib_2024)
        payment_ttnb = seed_payment_for_citizen(user, ttnb_2024)
        
        # Budget projects
        projects = seed_budget_projects_for_commune(1)
        seed_user_votes_on_budgets(user, projects)
        
        db.session.commit()
        print(f"✓ Seeded citizen demo flow:")
        print(f"  - Property #{prop.id}:")
        print(f"    • 2024 TIB (payable 2025): #{tib_2024.id} PAID ✓")
        print(f"    • 2025 TIB (payable 2026): #{tib_2025.id} PENDING")
        print(f"  - Land #{land.id}:")
        print(f"    • 2024 TTNB (payable 2025): #{ttnb_2024.id} PAID ✓")
        print(f"    • 2025 TTNB (payable 2026): PENDING")
        print(f"  - Payments: #{payment_tib.id} (2024 TIB), #{payment_ttnb.id} (2024 TTNB)")
        print(f"  - Budget projects: {len(projects)} with votes")


if __name__ == "__main__":
    main()
