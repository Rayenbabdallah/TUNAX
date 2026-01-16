#!/usr/bin/env python3
"""Quick check of seeded data"""
from extensions.db import db
from models.tax import Tax
from models.property import Property
from models.land import Land
from models.user import User

print("\n=== SEEDED DATA CHECK ===\n")

# Check users
users = User.query.limit(5).all()
print(f"Total Users: {User.query.count()}")
for u in users:
    print(f"  - {u.username} ({u.role.value}) | Email: {u.email}")

# Check properties
print(f"\nTotal Properties: {Property.query.count()}")
props = Property.query.limit(3).all()
for p in props:
    print(f"  - ID: {p.id}, Address: {p.street_address}, Owner: {p.owner_id}")

# Check lands
print(f"\nTotal Lands: {Land.query.count()}")
lands = Land.query.limit(3).all()
for l in lands:
    print(f"  - ID: {l.id}, Address: {l.street_address}, Owner: {l.owner_id}")

# Check taxes
print(f"\nTotal Taxes: {Tax.query.count()}")
taxes = Tax.query.limit(5).all()
for t in taxes:
    owner = t.property.owner_id if t.property else (t.land.owner_id if t.land else "?")
    print(f"  - ID: {t.id}, Type: {t.tax_type.value}, Status: {t.status.value}, Owner: {owner}, Amount: {t.tax_amount}")

print("\n" + "="*50 + "\n")
