#!/usr/bin/env python3
"""Reset all demo user passwords to default"""
from models.user import User
from extensions.db import db
from app import create_app

def main():
    app = create_app()
    with app.app_context():
        demo_users = [
            'demo_citizen', 'demo_business', 'demo_agent', 'demo_inspector',
            'demo_finance', 'demo_contentieux', 'demo_urbanism', 'demo_admin',
            'ministry_admin'
        ]
        
        for username in demo_users:
            u = User.query.filter_by(username=username).first()
            if u:
                u.set_password("TunaxDemo123!")
        
        db.session.commit()
        print('✓ All demo passwords reset to TunaxDemo123!')

if __name__ == "__main__":
    main()
