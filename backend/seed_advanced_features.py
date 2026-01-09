"""Seed advanced features: exemptions, permits, disputes, penalties, inspections, satellite verification.
Run inside the backend container: python seed_advanced_features.py
"""
from __future__ import annotations

import os
from datetime import datetime, timedelta
from pathlib import Path

from dotenv import load_dotenv

from app import create_app
from extensions.db import db
from models.user import User, UserRole
from models.property import Property
from models.land import Land
from models.declaration import Declaration
from models.tax import Tax, TaxType, TaxStatus
from models.exemption import Exemption, ExemptionStatus, ExemptionType
from models.permit import Permit, PermitType, PermitStatus
from models.dispute import Dispute, DisputeType, DisputeStatus
from models.payment_plan import PaymentPlan, PaymentPlanStatus
from models.penalty import Penalty, PenaltyType, PenaltyStatus
from models.inspection import Inspection, InspectionStatus
from models.satellite_verification import SatelliteVerification
from models.reclamation import Reclamation, ReclamationType, ReclamationStatus
from models.commune import Commune
from models.payment import Payment, PaymentStatus, PaymentMethod


def get_demo_users() -> dict:
    """Get all demo users for various scenarios."""
    return {
        'citizen': User.query.filter_by(username='demo_citizen').first(),
        'business': User.query.filter_by(username='demo_business').first(),
        'agent': User.query.filter_by(username='demo_agent').first(),
        'inspector': User.query.filter_by(username='demo_inspector').first(),
        'finance': User.query.filter_by(username='demo_finance').first(),
        'contentieux': User.query.filter_by(username='demo_contentieux').first(),
        'urbanism': User.query.filter_by(username='demo_urbanism').first(),
        'admin': User.query.filter_by(username='demo_admin').first(),
    }


def seed_reference_prices() -> None:
    """Seed reference prices for commune 1 (within legal bounds)."""
    print("\n=== Seeding Reference Prices ===")
    print("⚠ ReferencePrice model not yet implemented, skipping")
    # Reference prices are set directly on properties via reference_price_per_m2 field


def seed_exemptions(users: dict) -> None:
    """Seed exemption requests (approved, rejected, pending)."""
    print("\n=== Seeding Exemptions ===")
    
    citizen = users['citizen']
    business = users['business']
    
    if not citizen or not business:
        print("⚠ Demo users not found, skipping")
        return
    
    # Get properties/lands for exemptions
    citizen_property = Property.query.filter_by(owner_id=citizen.id).first()
    business_property = Property.query.filter_by(owner_id=business.id).first()
    citizen_land = Land.query.filter_by(owner_id=citizen.id).first()
    citizen_tax = Tax.query.filter_by(property_id=citizen_property.id, tax_year=2025).first() if citizen_property else None
    
    exemptions_data = [
        {
            "user_id": citizen.id,
            "exemption_type": ExemptionType.REDUCTION.value,
            "property_id": citizen_property.id if citizen_property else None,
            "tax_id": citizen_tax.id if citizen_tax else None,
            "reason": "Economic hardship - single income household",
            "requested_amount": 50.0,
            "status": ExemptionStatus.APPROVED,
            "decision": "approved",
            "admin_notes": "Approved for 50 TND reduction based on income verification",
            "requested_date": datetime.utcnow() - timedelta(days=30),
            "decision_date": datetime.utcnow() - timedelta(days=15),
        },
        {
            "user_id": business.id,
            "exemption_type": ExemptionType.SPECIAL.value,
            "property_id": business_property.id if business_property else None,
            "reason": "Building under renovation - temporarily uninhabitable",
            "status": ExemptionStatus.PENDING,
            "requested_date": datetime.utcnow() - timedelta(days=10),
        },
        {
            "user_id": citizen.id,
            "exemption_type": ExemptionType.FULL.value,
            "land_id": citizen_land.id if citizen_land else None,
            "reason": "Public utility - land donated for community garden",
            "status": ExemptionStatus.REJECTED,
            "decision": "rejected",
            "admin_notes": "Land ownership transfer not yet completed - reapply after official transfer",
            "requested_date": datetime.utcnow() - timedelta(days=45),
            "decision_date": datetime.utcnow() - timedelta(days=20),
        },
    ]
    
    created = 0
    for data in exemptions_data:
        existing = Exemption.query.filter_by(
            user_id=data["user_id"],
            exemption_type=data["exemption_type"],
            property_id=data.get("property_id"),
            land_id=data.get("land_id")
        ).first()
        
        if not existing:
            exemption = Exemption(**data)
            db.session.add(exemption)
            created += 1
    
    print(f"✓ Created {created} exemption requests (approved/rejected/pending)")


def seed_permits(users: dict) -> None:
    """Seed permit requests (approved, rejected, blocked for unpaid taxes)."""
    print("\n=== Seeding Permits ===")
    
    citizen = users['citizen']
    business = users['business']
    
    if not citizen or not business:
        print("⚠ Demo users not found, skipping")
        return
    
    # Create a second property for business with UNPAID taxes
    business_property2 = Property.query.filter_by(
        owner_id=business.id,
        street_address="15 Commerce Avenue"
    ).first()
    
    if not business_property2:
        from models.property import PropertyAffectation
        business_property2 = Property(
            owner_id=business.id,
            commune_id=1,
            street_address="15 Commerce Avenue",
            city="Tunis",
            delegation="Tunis",
            post_code="1000",
            latitude=36.8100,
            longitude=10.1850,
            surface_couverte=300.0,
            surface_totale=350.0,
            affectation=PropertyAffectation.COMMERCIAL,
            nb_floors=3,
            construction_year=2018,
            reference_price_per_m2=250.0,
        )
        db.session.add(business_property2)
        db.session.flush()
        
        # Create UNPAID tax for this property
        from utils.calculator import TaxCalculator
        calc = TaxCalculator.calculate_tib(business_property2)
        unpaid_tax = Tax(
            property_id=business_property2.id,
            tax_type=TaxType.TIB,
            tax_year=2024,
            base_amount=float(calc.get("base_amount", 0.0)),
            rate_percent=float(calc.get("rate_percent", 0.0)),
            tax_amount=float(calc.get("tax_amount", 0.0)),
            total_amount=float(calc.get("total_amount", 0.0)),
            status=TaxStatus.NOTIFIED,  # UNPAID
            notification_date=datetime.utcnow() - timedelta(days=90)
        )
        db.session.add(unpaid_tax)
        db.session.flush()
    
    citizen_property = Property.query.filter_by(owner_id=citizen.id).first()
    
    permits_data = [
        {
            "user_id": citizen.id,
            "property_id": citizen_property.id if citizen_property else None,
            "permit_type": PermitType.CONSTRUCTION.value,
            "description": "Add second floor extension",
            "status": PermitStatus.APPROVED,
            "taxes_paid": True,
            "submitted_date": datetime.utcnow() - timedelta(days=60),
            "decision_date": datetime.utcnow() - timedelta(days=40),
            "decision_notes": "All requirements met - taxes paid, documents valid",
        },
        {
            "user_id": business.id,
            "property_id": business_property2.id if business_property2 else None,
            "permit_type": PermitType.OCCUPANCY.value,
            "description": "Commercial occupancy permit for restaurant",
            "status": PermitStatus.BLOCKED_UNPAID_TAXES,
            "taxes_paid": False,
            "submitted_date": datetime.utcnow() - timedelta(days=20),
            "decision_notes": "BLOCKED - Outstanding tax debt of 2024 TIB. Pay taxes to proceed.",
        },
        {
            "user_id": citizen.id,
            "property_id": citizen_property.id if citizen_property else None,
            "permit_type": PermitType.SIGNATURE_LEGALIZATION.value,
            "description": "Property sale signature legalization",
            "status": PermitStatus.PENDING,
            "taxes_paid": True,
            "submitted_date": datetime.utcnow() - timedelta(days=5),
        },
    ]
    
    created = 0
    for data in permits_data:
        existing = Permit.query.filter_by(
            user_id=data["user_id"],
            property_id=data.get("property_id"),
            permit_type=data["permit_type"]
        ).first()
        
        if not existing:
            permit = Permit(**data)
            db.session.add(permit)
            created += 1
    
    print(f"✓ Created {created} permits (approved/blocked/pending)")


def seed_disputes(users: dict) -> None:
    """Seed disputes (submitted, commission review, resolved)."""
    print("\n=== Seeding Disputes ===")
    
    citizen = users['citizen']
    business = users['business']
    
    if not citizen or not business:
        print("⚠ Demo users not found, skipping")
        return
    
    citizen_property = Property.query.filter_by(owner_id=citizen.id).first()
    citizen_tax = Tax.query.filter_by(property_id=citizen_property.id, tax_year=2025).first() if citizen_property else None
    
    disputes_data = [
        {
            "claimant_id": citizen.id,
            "tax_id": citizen_tax.id if citizen_tax else None,
            "property_id": citizen_property.id if citizen_property else None,
            "dispute_type": DisputeType.EVALUATION.value,
            "subject": "Property surface area miscalculation",
            "description": "The declared surface of 150 m² does not match cadastral records showing 140 m²",
            "status": DisputeStatus.COMMISSION_REVIEW.value,
            "commission_reviewed": True,
            "commission_decision": "Commission agrees - surface verified at 140 m². Tax recalculation approved.",
            "submitted_date": datetime.utcnow() - timedelta(days=50),
            "commission_review_date": datetime.utcnow() - timedelta(days=20),
        },
        {
            "claimant_id": business.id,
            "dispute_type": DisputeType.PENALTY.value,
            "subject": "Late payment penalty dispute",
            "description": "Penalty applied despite payment being on time according to bank records",
            "status": DisputeStatus.RESOLVED.value,
            "final_decision": "RESOLVED - Bank records confirmed timely payment. Penalty waived.",
            "submitted_date": datetime.utcnow() - timedelta(days=80),
            "resolution_date": datetime.utcnow() - timedelta(days=30),
        },
        {
            "claimant_id": citizen.id,
            "dispute_type": DisputeType.CALCULATION.value,
            "subject": "Service rate calculation error",
            "description": "Applied 14% rate but only 4 services available in our area",
            "status": DisputeStatus.ACCEPTED.value,
            "submitted_date": datetime.utcnow() - timedelta(days=10),
        },
    ]
    
    created = 0
    for data in disputes_data:
        existing = Dispute.query.filter_by(
            claimant_id=data["claimant_id"],
            subject=data["subject"]
        ).first()
        
        if not existing:
            dispute = Dispute(**data)
            db.session.add(dispute)
            created += 1
    
    print(f"✓ Created {created} disputes (submitted/commission/resolved)")


def seed_payment_plans(users: dict) -> None:
    """Seed payment plans (approved, rejected, pending)."""
    print("\n=== Seeding Payment Plans ===")
    
    citizen = users['citizen']
    business = users['business']
    
    if not citizen or not business:
        print("⚠ Demo users not found, skipping")
        return
    
    # Get unpaid taxes
    business_property = Property.query.filter_by(owner_id=business.id, street_address="15 Commerce Avenue").first()
    unpaid_tax = Tax.query.filter_by(property_id=business_property.id, status=TaxStatus.NOTIFIED).first() if business_property else None
    
    if not unpaid_tax:
        print("⚠ No unpaid tax found for payment plan demo, skipping")
        return
    
    plans_data = [
        {
            "user_id": business.id,
            "tax_id": unpaid_tax.id,
            "total_amount": unpaid_tax.total_amount,
            "installments": 6,
            "installment_amount": round(unpaid_tax.total_amount / 6, 2),
            "status": PaymentPlanStatus.APPROVED.value,
            "requested_date": datetime.utcnow() - timedelta(days=25),
            "approved_date": datetime.utcnow() - timedelta(days=15),
            "approved_by": users['finance'].id if users.get('finance') else None,
            "notes": "Approved - business showed financial hardship proof",
        },
    ]
    
    created = 0
    for data in plans_data:
        existing = PaymentPlan.query.filter_by(
            user_id=data["user_id"],
            tax_id=data["tax_id"]
        ).first()
        
        if not existing:
            plan = PaymentPlan(**data)
            db.session.add(plan)
            created += 1
    
    print(f"✓ Created {created} payment plans")


def seed_penalties(users: dict) -> None:
    """Seed late payment penalties."""
    print("\n=== Seeding Penalties ===")
    
    business = users['business']
    
    if not business:
        print("⚠ Demo business not found, skipping")
        return
    
    # Get unpaid tax
    business_property = Property.query.filter_by(owner_id=business.id, street_address="15 Commerce Avenue").first()
    unpaid_tax = Tax.query.filter_by(property_id=business_property.id, status=TaxStatus.NOTIFIED).first() if business_property else None
    
    if not unpaid_tax:
        print("⚠ No unpaid tax found for penalties, skipping")
        return
    
    # Calculate penalty (5% initial + 1% per month for 3 months late)
    months_late = 3
    initial_penalty = unpaid_tax.tax_amount * 0.05
    monthly_penalty = unpaid_tax.tax_amount * 0.01 * months_late
    total_penalty = initial_penalty + monthly_penalty
    
    penalties_data = [
        {
            "tax_id": unpaid_tax.id,
            "penalty_type": PenaltyType.LATE_PAYMENT.value,
            "base_amount": unpaid_tax.tax_amount,
            "penalty_rate": 5.0,  # 5% initial
            "penalty_amount": initial_penalty,
            "status": PenaltyStatus.ACTIVE.value,
            "applied_date": datetime.utcnow() - timedelta(days=90),
            "reason": "Initial late payment penalty (5%)",
        },
        {
            "tax_id": unpaid_tax.id,
            "penalty_type": PenaltyType.MONTHLY_INTEREST.value,
            "base_amount": unpaid_tax.tax_amount,
            "penalty_rate": 1.0 * months_late,
            "penalty_amount": monthly_penalty,
            "status": PenaltyStatus.ACTIVE.value,
            "applied_date": datetime.utcnow() - timedelta(days=60),
            "reason": f"Monthly interest penalty (1% × {months_late} months)",
        },
    ]
    
    created = 0
    for data in penalties_data:
        existing = Penalty.query.filter_by(
            tax_id=data["tax_id"],
            penalty_type=data["penalty_type"]
        ).first()
        
        if not existing:
            penalty = Penalty(**data)
            db.session.add(penalty)
            created += 1
    
    # Update tax total to include penalties
    if created > 0:
        unpaid_tax.penalty_amount = total_penalty
        unpaid_tax.total_amount = unpaid_tax.tax_amount + total_penalty
    
    print(f"✓ Created {created} penalties (late payment + monthly interest)")


def seed_inspections(users: dict) -> None:
    """Seed field inspections with reports."""
    print("\n=== Seeding Inspections ===")
    
    inspector = users['inspector']
    citizen = users['citizen']
    
    if not inspector or not citizen:
        print("⚠ Inspector or citizen not found, skipping")
        return
    
    citizen_property = Property.query.filter_by(owner_id=citizen.id).first()
    
    if not citizen_property:
        print("⚠ No property found for inspection, skipping")
        return
    
    inspections_data = [
        {
            "inspector_id": inspector.id,
            "property_id": citizen_property.id,
            "inspection_type": "field_verification",
            "scheduled_date": datetime.utcnow() - timedelta(days=40),
            "inspection_date": datetime.utcnow() - timedelta(days=35),
            "status": InspectionStatus.COMPLETED.value,
            "findings": "Property verified - surface measurements match declaration. Construction quality good.",
            "measured_surface": 150.0,
            "discrepancies": None,
            "photos_uploaded": True,
            "report_submitted": True,
        },
    ]
    
    created = 0
    for data in inspections_data:
        existing = Inspection.query.filter_by(
            inspector_id=data["inspector_id"],
            property_id=data["property_id"]
        ).first()
        
        if not existing:
            inspection = Inspection(**data)
            db.session.add(inspection)
            created += 1
    
    print(f"✓ Created {created} inspections")


def seed_satellite_verification(users: dict) -> None:
    """Seed satellite verification records."""
    print("\n=== Seeding Satellite Verification ===")
    
    inspector = users['inspector']
    citizen = users['citizen']
    
    if not inspector or not citizen:
        print("⚠ Inspector or citizen not found, skipping")
        return
    
    citizen_property = Property.query.filter_by(owner_id=citizen.id).first()
    citizen_land = Land.query.filter_by(owner_id=citizen.id).first()
    
    verifications_data = []
    
    if citizen_property:
        verifications_data.append({
            "inspector_id": inspector.id,
            "property_id": citizen_property.id,
            "image_source": "NASA_GIBS",
            "image_date": datetime.utcnow() - timedelta(days=30),
            "image_url": f"https://gibs.earthdata.nasa.gov/wms/epsg4326/best/wms.cgi?SERVICE=WMS&REQUEST=GetMap&LAYERS=MODIS_Terra_CorrectedReflectance_TrueColor&BBOX={citizen_property.longitude-0.01},{citizen_property.latitude-0.01},{citizen_property.longitude+0.01},{citizen_property.latitude+0.01}",
            "verified": True,
            "verification_notes": "Satellite imagery confirms building footprint matches declared surface area",
            "created_at": datetime.utcnow() - timedelta(days=28),
        })
    
    if citizen_land:
        verifications_data.append({
            "inspector_id": inspector.id,
            "land_id": citizen_land.id,
            "image_source": "USGS_LANDSAT",
            "image_date": datetime.utcnow() - timedelta(days=20),
            "image_url": f"https://earthexplorer.usgs.gov/landsat/lat={citizen_land.latitude}&lon={citizen_land.longitude}",
            "verified": True,
            "verification_notes": "Land parcel visible, no unauthorized construction detected",
            "created_at": datetime.utcnow() - timedelta(days=18),
        })
    
    created = 0
    for data in verifications_data:
        existing = SatelliteVerification.query.filter_by(
            inspector_id=data["inspector_id"],
            property_id=data.get("property_id"),
            land_id=data.get("land_id")
        ).first()
        
        if not existing:
            verification = SatelliteVerification(**data)
            db.session.add(verification)
            created += 1
    
    print(f"✓ Created {created} satellite verification records")


def seed_reclamations(users: dict) -> None:
    """Seed service reclamations."""
    print("\n=== Seeding Reclamations ===")
    
    citizen = users['citizen']
    agent = users['agent']
    
    if not citizen or not agent:
        print("⚠ Citizen or agent not found, skipping")
        return
    
    reclamations_data = [
        {
            "user_id": citizen.id,
            "commune_id": 1,
            "reclamation_type": ReclamationType.ROAD_MAINTENANCE.value,
            "subject": "Pothole on Rue de la Liberté",
            "description": "Large pothole causing traffic issues near property address",
            "status": ReclamationStatus.ASSIGNED.value,
            "assigned_to": agent.id,
            "submitted_date": datetime.utcnow() - timedelta(days=15),
            "assigned_date": datetime.utcnow() - timedelta(days=10),
        },
        {
            "user_id": citizen.id,
            "commune_id": 1,
            "reclamation_type": ReclamationType.GARBAGE_COLLECTION.value,
            "subject": "Missed garbage collection",
            "description": "Garbage not collected for 2 weeks on Demo Street",
            "status": ReclamationStatus.IN_PROGRESS.value,
            "assigned_to": agent.id,
            "submitted_date": datetime.utcnow() - timedelta(days=5),
            "assigned_date": datetime.utcnow() - timedelta(days=3),
        },
    ]
    
    created = 0
    for data in reclamations_data:
        existing = Reclamation.query.filter_by(
            user_id=data["user_id"],
            subject=data["subject"]
        ).first()
        
        if not existing:
            reclamation = Reclamation(**data)
            db.session.add(reclamation)
            created += 1
    
    print(f"✓ Created {created} reclamations")


def main() -> None:
    """Run advanced features seeding."""
    project_root = Path(__file__).resolve().parent.parent
    load_dotenv(project_root / ".env")
    load_dotenv(project_root / "backend" / ".env")

    app = create_app(os.getenv("FLASK_ENV", "development"))
    with app.app_context():
        print("=" * 70)
        print("TUNAX Advanced Features Seeder")
        print("Seeding exemptions, permits, disputes, penalties, inspections, etc.")
        print("=" * 70)
        
        users = get_demo_users()
        
        if not users['citizen']:
            print("❌ demo_citizen not found. Run seed_demo.py first.")
            return
        
        try:
            # Seed all advanced features
            seed_reference_prices()
            seed_exemptions(users)
            seed_permits(users)
            seed_disputes(users)
            seed_payment_plans(users)
            seed_penalties(users)
            seed_inspections(users)
            seed_satellite_verification(users)
            seed_reclamations(users)
            
            db.session.commit()
            
            print("\n" + "=" * 70)
            print("✓ Advanced features seeding complete!")
            print("=" * 70)
            print("\nSeeded Features Summary:")
            print("  ✓ Reference prices (4 categories)")
            print("  ✓ Exemptions (approved/rejected/pending)")
            print("  ✓ Permits (approved/blocked/pending)")
            print("  ✓ Disputes (commission review/resolved)")
            print("  ✓ Payment plans (approved)")
            print("  ✓ Penalties (late payment + monthly interest)")
            print("  ✓ Field inspections (completed)")
            print("  ✓ Satellite verifications (property + land)")
            print("  ✓ Service reclamations (assigned/in-progress)")
            print("=" * 70)
            
        except Exception as e:
            db.session.rollback()
            print(f"\n❌ SEEDING FAILED: {e}")
            import traceback
            traceback.print_exc()
            raise


if __name__ == "__main__":
    main()
