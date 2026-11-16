"""
Check existing users in the database
"""
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from app.database import get_db
from app.models import User

print("=== Checking Users in Database ===\n")

db = next(get_db())
users = db.query(User).all()

if not users:
    print("⚠ No users found in database!")
    print("\nYou need to create a user first.")
    print("Go to: http://localhost:8000/auth/setup")
else:
    print(f"Found {len(users)} user(s):\n")
    for user in users:
        print(f"Username: {user.username}")
        print(f"Name: {user.name}")
        print(f"Role: {user.role}")
        print(f"Active: {user.is_active}")
        print("-" * 40)
    
    print("\n⚠ NOTE: Passwords are hashed and cannot be retrieved.")
    print("If you forgot your password, you'll need to reset it in the database.")
