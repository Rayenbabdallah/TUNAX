"""Seed the database with one demo user for each role."""
from __future__ import annotations

import os
import pyotp
import json
from typing import List
from pathlib import Path

from dotenv import load_dotenv

from app import create_app
from extensions.db import db
from models.user import User, UserRole
from models.two_factor import TwoFactorAuth

# Default password used for all demo accounts (can be overridden via env var)
DEFAULT_PASSWORD = os.getenv("DEMO_USER_PASSWORD", "TunaxDemo123!")


def build_demo_users() -> list:
    """Return the attributes for each demo user."""
    return [
        {
            "role": UserRole.CITIZEN,
            "username": "demo_citizen",
            "email": "citizen.demo@tunax.tn",
            "first_name": "Amine",
            "last_name": "Citizen",
            "phone": "+21611111111",
            "cin": "CITIZEN001",
        },
        {
            "role": UserRole.BUSINESS,
            "username": "demo_business",
            "email": "business.demo@tunax.tn",
            "first_name": "Sara",
            "last_name": "Enterprise",
            "phone": "+21622222222",
            "business_name": "Demo Industries",
            "business_registration": "TN-DEM-001",
        },
        {
            "role": UserRole.MUNICIPAL_AGENT,
            "username": "demo_agent",
            "email": "agent.demo@tunax.tn",
            "first_name": "Hedi",
            "last_name": "Agent",
            "phone": "+21633333333",
            "commune_id": 1,
        },
        {
            "role": UserRole.INSPECTOR,
            "username": "demo_inspector",
            "email": "inspector.demo@tunax.tn",
            "first_name": "Mariem",
            "last_name": "Inspector",
            "phone": "+21644444444",
            "commune_id": 1,
        },
        {
            "role": UserRole.FINANCE_OFFICER,
            "username": "demo_finance",
            "email": "finance.demo@tunax.tn",
            "first_name": "Fares",
            "last_name": "Finance",
            "phone": "+21655555555",
            "commune_id": 1,
        },
        {
            "role": UserRole.CONTENTIEUX_OFFICER,
            "username": "demo_contentieux",
            "email": "contentieux.demo@tunax.tn",
            "first_name": "Nadia",
            "last_name": "Contentieux",
            "phone": "+21666666666",
            "commune_id": 1,
        },
        {
            "role": UserRole.URBANISM_OFFICER,
            "username": "demo_urbanism",
            "email": "urbanism.demo@tunax.tn",
            "first_name": "Youssef",
            "last_name": "Urbanism",
            "phone": "+21677777777",
            "commune_id": 1,
        },
        {
            "role": UserRole.MUNICIPAL_ADMIN,
            "username": "demo_admin",
            "email": "admin.demo@tunax.tn",
            "first_name": "Leila",
            "last_name": "Admin",
            "phone": "+21688888888",
            "commune_id": 1,
        },
        {
            "role": UserRole.MINISTRY_ADMIN,
            "username": "ministry_admin",
            "email": "ministry@tunax.tn",
            "first_name": "Mohamed",
            "last_name": "Ministry",
            "phone": "+21699999999",
            "commune_id": None,  # Ministry level - no specific commune
        },
    ]


def seed_demo_users() -> None:
    """Create one user per role if it does not already exist."""
    demo_users = build_demo_users()
    created = []
    updated = []

    for user_data in demo_users:
        role = user_data["role"]
        username = user_data["username"]
        user = User.query.filter_by(username=username).first()

        if user:
            action_list = updated
        else:
            user = User(username=username, role=role)
            db.session.add(user)
            action_list = created

        # Ensure consistent profile info and creds even if the user already existed
        user.email = user_data["email"]
        user.first_name = user_data.get("first_name")
        user.last_name = user_data.get("last_name")
        user.phone = user_data.get("phone")
        user.cin = user_data.get("cin")
        user.business_name = user_data.get("business_name")
        user.business_registration = user_data.get("business_registration")
        user.is_active = True
        user.role = role
        user.commune_id = user_data.get("commune_id")
        user.set_password(DEFAULT_PASSWORD)
        action_list.append(username)

    db.session.commit()

    print(f"Created users: {created}" if created else "No new users created.")
    if updated:
        print(f"Updated existing users: {updated}")
    print("\n✓ All demo users ready (2FA disabled by default)")


def main() -> None:
    """Run the seeding script inside the app context."""
    project_root = Path(__file__).resolve().parent.parent
    load_dotenv(project_root / ".env")
    load_dotenv(project_root / "backend" / ".env")

    app = create_app(os.getenv("FLASK_ENV", "development"))
    with app.app_context():
        seed_demo_users()


if __name__ == "__main__":
    main()
