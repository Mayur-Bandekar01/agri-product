"""
Verify complete project setup
"""
import sys
import os
import subprocess

print("═" * 70)
print("    ADINATH AGRI SERVICES - SETUP VERIFICATION")
print("═" * 70)
print()

errors = []
warnings = []
success = []

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

# 1. Check Python version
print("1. Checking Python version...")
version = sys.version_info
if version.major == 3 and version.minor >= 10:
    success.append(f"✓ Python {version.major}.{version.minor}.{version.micro}")
else:
    errors.append(f"✗ Python version {version.major}.{version.minor} (need 3.10+)")

# 2. Check virtual environment
print("2. Checking virtual environment...")
venv_path = os.path.join(os.path.dirname(__file__), 'backend', 'venv')
if os.path.exists(venv_path):
    success.append("✓ Virtual environment exists")
else:
    errors.append("✗ Virtual environment not found at backend/venv")

# 3. Check required packages
print("3. Checking required packages...")
required = ['fastapi', 'uvicorn', 'sqlalchemy', 'passlib', 'jose', 'openpyxl']
installed = []
missing = []

for package in required:
    try:
        if package == 'jose':
            __import__('jose')
        else:
            __import__(package)
        installed.append(package)
    except ImportError:
        missing.append(package)

if missing:
    errors.append(f"✗ Missing packages: {', '.join(missing)}")
    print(f"   To fix: pip install -r requirements.txt")
else:
    success.append(f"✓ All {len(required)} required packages installed")

# 4. Check database
print("4. Checking database...")
db_path = os.path.join(os.path.dirname(__file__), 'backend', 'adinath.db')
if os.path.exists(db_path):
    size_mb = os.path.getsize(db_path) / (1024 * 1024)
    success.append(f"✓ Database exists ({size_mb:.2f} MB)")
    
    # Check database content
    try:
        from app.database import get_db
        from app.models import Product, User
        from sqlalchemy import func
        
        db = next(get_db())
        product_count = db.query(func.count(Product.id)).scalar()
        user_count = db.query(func.count(User.id)).scalar()
        
        success.append(f"✓ Database has {product_count} products")
        success.append(f"✓ Database has {user_count} user(s)")
        
        if product_count < 110:
            warnings.append(f"⚠ Expected 110 products, found {product_count}")
    except Exception as e:
        errors.append(f"✗ Database error: {str(e)}")
else:
    errors.append("✗ Database not found at backend/adinath.db")

# 5. Check backups directory
print("5. Checking backups...")
backup_dir = os.path.join(os.path.dirname(__file__), 'backend', 'backups')
if os.path.exists(backup_dir):
    backups = [f for f in os.listdir(backup_dir) if f.endswith('.db')]
    success.append(f"✓ Backup directory exists ({len(backups)} backups)")
else:
    warnings.append("⚠ Backup directory not found")

# 6. Check frontend
print("6. Checking frontend...")
frontend_dir = os.path.join(os.path.dirname(__file__), 'frontend')
if os.path.exists(os.path.join(frontend_dir, 'index.html')):
    success.append("✓ Frontend files exist")
else:
    errors.append("✗ Frontend index.html not found")

# 7. Check start script
print("7. Checking start script...")
start_script = os.path.join(os.path.dirname(__file__), 'start-backend.bat')
if os.path.exists(start_script):
    success.append("✓ start-backend.bat exists")
else:
    warnings.append("⚠ start-backend.bat not found")

# 8. Check requirements.txt
print("8. Checking requirements.txt...")
req_file = os.path.join(os.path.dirname(__file__), 'backend', 'requirements.txt')
if os.path.exists(req_file):
    with open(req_file, 'r') as f:
        packages = [line.strip() for line in f if line.strip() and not line.startswith('#')]
    success.append(f"✓ requirements.txt exists ({len(packages)} packages)")
else:
    errors.append("✗ requirements.txt not found")

# 9. Check admin user
print("9. Checking admin user...")
try:
    from app.database import get_db
    from app.models import User
    
    db = next(get_db())
    admin = db.query(User).filter(User.username == 'admin').first()
    
    if admin:
        success.append(f"✓ Admin user exists ({admin.name})")
    else:
        warnings.append("⚠ Admin user not found (run create_admin.py)")
except Exception as e:
    errors.append(f"✗ Could not check admin user: {str(e)}")

print()
print("═" * 70)
print("                         RESULTS")
print("═" * 70)
print()

if success:
    print("✅ SUCCESS:")
    for item in success:
        print(f"   {item}")
    print()

if warnings:
    print("⚠️  WARNINGS:")
    for item in warnings:
        print(f"   {item}")
    print()

if errors:
    print("❌ ERRORS:")
    for item in errors:
        print(f"   {item}")
    print()
    print("═" * 70)
    print("Please fix the errors above before running the application.")
    print("See PROJECT_SETUP.md for detailed instructions.")
    sys.exit(1)
else:
    print("═" * 70)
    print("✅ ALL CHECKS PASSED - PROJECT IS READY TO RUN!")
    print("═" * 70)
    print()
    print("To start the application:")
    print()
    print("  Option 1: Double-click start-backend.bat")
    print("  Option 2: Run manually:")
    print("     cd backend")
    print("     .\\venv\\Scripts\\Activate.ps1")
    print("     python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000")
    print()
    print("Then open: http://localhost:8000")
    print("Login: admin / admin123")
    print()
    print("═" * 70)
