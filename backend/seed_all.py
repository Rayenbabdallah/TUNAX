"""Unified seeding script for TUNAX.
Runs all individual seeders in the correct order so you can initialize
and demo the application quickly.

Usage (inside Docker):
  docker-compose exec backend python seed_all.py
"""
from __future__ import annotations

import os
import importlib
from pathlib import Path

from dotenv import load_dotenv

# Seed modules to run in order
SEED_MODULES = [
    "seed_communes",              # communes, reference prices, services, ministry admin
    "seed_demo",                 # demo users for all roles
    "seed_test_resources",       # document types + sample test document
    "seed_demo_citizen_flow",    # property + declaration + TIB + sample doc for demo_citizen
    "seed_advanced_features",    # exemptions, permits, disputes, penalties, inspections, satellite verification
]


def run_module_main(mod_name: str) -> None:
    print(f"\n>>> Running {mod_name}.main()")
    mod = importlib.import_module(mod_name)
    if hasattr(mod, "main"):
        mod.main()
    else:
        print(f"[WARN] {mod_name} has no main(); skipping")


def main() -> None:
    project_root = Path(__file__).resolve().parent.parent
    load_dotenv(project_root / ".env")
    load_dotenv(project_root / "backend" / ".env")

    print("=" * 70)
    print("TUNAX Unified Seeder")
    print("Seeding: communes, users, test resources, citizen flow, advanced features")
    print("=" * 70)

    for name in SEED_MODULES:
        try:
            run_module_main(name)
        except Exception as e:
            print(f"[ERROR] {name} failed: {e}")
            import traceback
            traceback.print_exc()
            # continue to next to be resilient, unless you prefer to abort
            # break

    print("\n" + "=" * 70)
    print("✓ Unified seeding complete!")
    print("\nAll project features now have demo data:")
    print("  ✓ Properties & Lands (TIB/TTNB)")
    print("  ✓ Taxes (paid & unpaid with penalties)")
    print("  ✓ Exemptions (approved/rejected/pending)")
    print("  ✓ Permits (approved/blocked/pending)")
    print("  ✓ Disputes (commission review/resolved)")
    print("  ✓ Payment Plans (approved)")
    print("  ✓ Inspections & Satellite Verification")
    print("  ✓ Reclamations (assigned/in-progress)")
    print("  ✓ Budget Voting & Notifications")
    print("\nLogin: POST /api/v1/auth/login")
    print("Body: {\"username\": \"demo_citizen\", \"password\": \"TunaxDemo123!\"}")
    print("=" * 70)


if __name__ == "__main__":
    main()
