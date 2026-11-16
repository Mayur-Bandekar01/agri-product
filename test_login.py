"""
Test login functionality
"""
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from app.database import get_db
from app.models import User
from app.auth import hash_password, verify_password, authenticate_user

print("=== Testing Login Functionality ===\n")

db = next(get_db())

# Get admin user
user = db.query(User).filter(User.username == "admin").first()

if not user:
    print("✗ Admin user not found!")
    sys.exit(1)

print(f"Found user: {user.username}")
print(f"Name: {user.name}")
print(f"Role: {user.role}")
print(f"Active: {user.is_active}")
print(f"Password hash (first 20 chars): {user.password_hash[:20]}...")

# Test password verification
test_password = "admin123"
print(f"\nTesting password: '{test_password}'")

is_valid = verify_password(test_password, user.password_hash)
print(f"Password valid: {is_valid}")

if not is_valid:
    print("\n⚠ Password verification failed!")
    print("Resetting password...")
    
    new_hash = hash_password(test_password)
    print(f"New hash (first 20 chars): {new_hash[:20]}...")
    
    user.password_hash = new_hash
    db.commit()
    
    # Test again
    is_valid = verify_password(test_password, user.password_hash)
    print(f"Password valid after reset: {is_valid}")

# Test authenticate_user
print("\n--- Testing authenticate_user function ---")
authenticated_user = authenticate_user(db, "admin", "admin123")
if authenticated_user:
    print("✓ Authentication successful!")
    print(f"Authenticated as: {authenticated_user.name}")
else:
    print("✗ Authentication failed!")
