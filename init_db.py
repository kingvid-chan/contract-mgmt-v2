"""
Database initialization script.
Creates all tables and inserts preset user accounts:
  - admin / admin123 (administrator)
  - demo  / demo123  (regular user)
"""
import os
import sys

import bcrypt

# Ensure the project root is on the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from models import db, User

app = create_app()

with app.app_context():
    db.create_all()
    print("Database tables created.")

    # Preset admin account
    if not User.query.filter_by(username="admin").first():
        admin_hash = bcrypt.hashpw(b"admin123", bcrypt.gensalt())
        admin = User(
            username="admin",
            password_hash=admin_hash.decode("utf-8"),
            role="admin",
            is_active=True,
        )
        db.session.add(admin)
        print("Admin user created: admin / admin123")
    else:
        print("Admin user already exists, skipping.")

    # Preset demo account
    if not User.query.filter_by(username="demo").first():
        demo_hash = bcrypt.hashpw(b"demo123", bcrypt.gensalt())
        demo = User(
            username="demo",
            password_hash=demo_hash.decode("utf-8"),
            role="user",
            is_active=True,
        )
        db.session.add(demo)
        print("Demo user created: demo / demo123")
    else:
        print("Demo user already exists, skipping.")

    db.session.commit()
    print("Database initialization complete.")
