"""
Reset user password
"""
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from app.database import get_db
from app.models import User
from app.auth import hash_password

print("=== Reset User Password ===\n")

username = input("Enter username (default: sanket): ").strip() or "sanket"
new_password = input("Enter new password (default: admin123): ").strip() or "admin123"

db = next(get_db())
user = db.query(User).filter(User.username == username).first()

if not user:
    print(f"\n✗ User '{username}' not found!")
    sys.exit(1)

# Update password
user.hashed_password = hash_password(new_password)
db.commit()

print(f"\n✓ Password updated successfully!")
print(f"\nLogin credentials:")
print(f"  Username: {username}")
print(f"  Password: {new_password}")
print(f"\nYou can now login at: http://localhost:8000")
