"""
Create a new admin user or update existing one
"""
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from app.database import get_db
from app.models import User, RoleEnum
from app.auth import hash_password
from datetime import datetime

print("=== Create/Update Admin User ===\n")

# Default credentials
username = "admin"
password = "admin123"
name = "Administrator"

db = next(get_db())

# Check if user exists
user = db.query(User).filter(User.username == username).first()

if user:
    print(f"User '{username}' already exists. Updating password...")
    user.password_hash = hash_password(password)
    user.is_active = True
    user.role = RoleEnum.admin
    db.commit()
    print("✓ Password updated!")
else:
    print(f"Creating new user '{username}'...")
    new_user = User(
        username=username,
        name=name,
        password_hash=hash_password(password),
        role=RoleEnum.admin,
        is_active=True
    )
    db.add(new_user)
    db.commit()
    print("✓ User created!")

print(f"\n{'='*50}")
print(f"LOGIN CREDENTIALS:")
print(f"{'='*50}")
print(f"Username: {username}")
print(f"Password: {password}")
print(f"{'='*50}")
print(f"\nLogin at: http://localhost:8000")
print("\nYou can now access:")
print("  - Frontend: http://localhost:8000")
print("  - API Docs: http://localhost:8000/docs")
