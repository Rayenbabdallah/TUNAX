"""Seed test resources needed by the Insomnia test collection."""
from __future__ import annotations

import os
from datetime import datetime, timedelta
from pathlib import Path

from dotenv import load_dotenv

from app import create_app
from extensions.db import db
from models.user import User, UserRole
from models.notification import Notification, NotificationStatus
from models.municipal_config import MunicipalServiceConfig, DocumentRequirement


def seed_reclamations():
    """Create sample reclamations for testing - DISABLED to prevent corruption."""
    print("\n=== Seeding Reclamations ===")
    print("⚠ Reclamations seeding disabled to prevent database corruption")
    print("✓ Skipped reclamations")


def seed_notifications():
    """Create sample notifications for testing."""
    print("\n=== Seeding Notifications ===")
    
    # Get demo users
    demo_citizen = User.query.filter_by(username="demo_citizen").first()
    demo_business = User.query.filter_by(username="demo_business").first()
    demo_agent = User.query.filter_by(username="demo_agent").first()
    demo_municipal = User.query.filter_by(username="demo_municipal").first()
    
    if not demo_citizen:
        print("⚠ Demo citizen not found. Run seed_demo.py first.")
        return
    
    notifications_data = [
        {
            "user_id": demo_citizen.id,
            "title": "Tax payment reminder",
            "message": "Your property tax payment is due in 15 days.",
            "notification_type": "payment_reminder",
            "status": NotificationStatus.UNREAD,
        },
        {
            "user_id": demo_citizen.id,
            "title": "Declaration approved",
            "message": "Your property tax declaration has been approved.",
            "notification_type": "declaration_status",
            "status": NotificationStatus.READ,
            "read_at": datetime.utcnow(),
        },
        {
            "user_id": demo_business.id if demo_business else demo_citizen.id,
            "title": "New tax regulation",
            "message": "New business tax regulations are now in effect.",
            "notification_type": "announcement",
            "status": NotificationStatus.UNREAD,
        },
        {
            "user_id": demo_agent.id if demo_agent else demo_citizen.id,
            "title": "New reclamation assigned",
            "message": "A new tax reclamation has been assigned to you.",
            "notification_type": "reclamation_assigned",
            "status": NotificationStatus.UNREAD,
        },
        {
            "user_id": demo_municipal.id if demo_municipal else demo_citizen.id,
            "title": "Monthly report ready",
            "message": "The monthly tax collection report is ready for review.",
            "notification_type": "report",
            "status": NotificationStatus.UNREAD,
        },
    ]
    
    created = []
    for data in notifications_data:
        # Check if similar notification exists
        existing = Notification.query.filter_by(
            user_id=data["user_id"],
            title=data["title"]
        ).first()
        
        if not existing:
            notification = Notification(**data)
            db.session.add(notification)
            created.append(data["title"])
    
    # Don't commit yet - will commit all at once
    print(f"✓ Created {len(created)} notifications: {created}")


def seed_municipal_services():
    """Create sample municipal service configs for testing."""
    print("\n=== Seeding Municipal Service Configs ===")
    
    try:
        # Check if service ID=1 exists (needed for tests)
        svc = MunicipalServiceConfig.query.filter_by(id=1).first()
        
        if not svc:
            # Create service with specific ID=1 for tests
            svc = MunicipalServiceConfig(
                id=1,
                commune_id=1,
                service_name='Test Service',
                service_code='test_service',
                is_available=True
            )
            db.session.add(svc)
            db.session.flush()  # Flush to assign ID
            print("✓ Created service with ID=1 for tests")
        else:
            print("✓ Service ID=1 already exists")
            
    except Exception as e:
        print(f"⚠ Service seeding error: {e}")
        db.session.rollback()


def seed_document_requirements():
    """Create sample document requirements for testing."""
    print("\n=== Seeding Document Requirements ===")
    
    try:
        # Check if document requirement ID=1 exists (needed for tests)
        doc = DocumentRequirement.query.filter_by(id=1).first()
        
        if not doc:
            # Create document requirement with specific ID=1 for tests
            doc = DocumentRequirement(
                id=1,
                commune_id=1,
                declaration_type='property',
                document_name='Test Document',
                document_code='test_doc',
                is_mandatory=True,
                display_order=1
            )
            db.session.add(doc)
            db.session.flush()  # Flush to assign ID
            print("✓ Created document requirement with ID=1 for tests")
        else:
            print("✓ Document requirement ID=1 already exists")
            
    except Exception as e:
        print(f"⚠ Document requirement seeding error: {e}")
        db.session.rollback()


def seed_payment_plans():
    """Create sample payment plan for testing."""
    print("\n=== Seeding Payment Plans ===")
    print("⚠ Payment plan table not yet created in schema, skipping")


def seed_document_types():
    """Create sample document types for testing aligned to current schema."""
    print("\n=== Seeding Document Types ===")
    try:
        from models.document import DocumentType
        # Seed common types for commune_id=1
        base_types = [
            ("TITLE_DEED", "Title Deed", True),
            ("TAX_RECEIPT", "Tax Receipt", False),
            ("CADASTRAL_PLAN", "Cadastral Plan", True),
            ("CONSTRUCTION_PERMIT", "Construction Permit", False),
            ("ID_DOCUMENT", "ID Document", True),
            ("OTHER", "Other", False),
        ]
        created = 0
        for code, label, required in base_types:
            existing = DocumentType.query.filter_by(commune_id=1, code=code).first()
            if not existing:
                dt = DocumentType(
                    commune_id=1,
                    code=code,
                    label=label,
                    is_required=required,
                    is_active=True,
                )
                db.session.add(dt)
                created += 1
        print(f"✓ Seeded {created} new document types (commune_id=1)")
    except Exception as e:
        print(f"⚠ Document types seeding error: {e}")
        db.session.rollback()


def seed_test_documents():
    """Create test document records using current Document schema."""
    print("\n=== Seeding Test Documents ===")
    try:
        from models.document import Document, DocumentType, DocumentStatus
        from models.declaration import Declaration
        
        declaration = Declaration.query.first()
        if not declaration:
            print("⚠ No declaration found, skipping document creation")
            return

        # Ensure a document type exists
        doc_type = DocumentType.query.filter_by(commune_id=declaration.commune_id).first()
        if not doc_type:
            doc_type = DocumentType(
                commune_id=declaration.commune_id,
                code="ID_DOCUMENT",
                label="ID Document",
                is_required=True,
                is_active=True,
            )
            db.session.add(doc_type)
            db.session.flush()

        # Create a storage file path
        storage_root = os.getenv("DOCUMENTS_STORAGE_PATH", "storage/documents")
        decl_dir = os.path.join(storage_root, str(declaration.id))
        os.makedirs(decl_dir, exist_ok=True)
        file_path = os.path.join(decl_dir, "seed_test.pdf")
        # Touch the file with sample content
        with open(file_path, "wb") as f:
            f.write(b"%PDF-1.4\n% Seed test file\n")

        document = Document(
            declaration_id=declaration.id,
            document_type_id=doc_type.id,
            uploader_id=declaration.owner_id,
            storage_path=file_path,
            file_name="seed_test.pdf",
            mime_type="application/pdf",
            file_size=os.path.getsize(file_path),
            status=DocumentStatus.APPROVED,
            version=1,
        )
        db.session.add(document)
        print(f"✓ Created seed test document for declaration {declaration.id}")
    except Exception as e:
        print(f"⚠ Document seeding error: {e}")
        db.session.rollback()


def main() -> None:
    """Run the test resource seeding script."""
    project_root = Path(__file__).resolve().parent.parent
    load_dotenv(project_root / ".env")
    load_dotenv(project_root / "backend" / ".env")

    app = create_app(os.getenv("FLASK_ENV", "development"))
    with app.app_context():
        print("=" * 60)
        print("SEEDING TEST RESOURCES")
        print("=" * 60)
        
        try:
            # Only seed non-problematic resources
            # Reclamations disabled - causes user corruption
            seed_reclamations()  # Disabled inside function
            seed_notifications()
            seed_municipal_services()
            seed_document_requirements()
            seed_payment_plans()
            seed_document_types()
            seed_test_documents()
            
            # Final commit
            db.session.commit()
            
            print("\n" + "=" * 60)
            print("✓ TEST RESOURCE SEEDING COMPLETE (Safe mode)")
            print("=" * 60)
        except Exception as e:
            db.session.rollback()
            print(f"\n❌ SEEDING FAILED: {e}")
            import traceback
            traceback.print_exc()
            raise


if __name__ == "__main__":
    main()
