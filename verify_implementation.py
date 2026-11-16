#!/usr/bin/env python3
"""
Verification Script for CA Export Implementation
Checks all components are working correctly
"""

import sys
import os

# Color codes for terminal output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'

def print_success(msg):
    print(f"{GREEN}✅ {msg}{RESET}")

def print_error(msg):
    print(f"{RED}❌ {msg}{RESET}")

def print_warning(msg):
    print(f"{YELLOW}⚠️  {msg}{RESET}")

def print_info(msg):
    print(f"{BLUE}ℹ️  {msg}{RESET}")

def check_imports():
    """Check if all modules can be imported"""
    print("\n" + "="*70)
    print("CHECKING MODULE IMPORTS")
    print("="*70)
    
    checks = []
    
    # Test CA Export Router
    try:
        from app.routers import ca_export
        print_success("CA Export router imports successfully")
        checks.append(True)
    except Exception as e:
        print_error(f"CA Export router import failed: {e}")
        checks.append(False)
    
    # Test Models
    try:
        from app.models import Product
        print_success("Models import successfully")
        
        # Check if new fields exist in model
        if hasattr(Product, 'hsn_code'):
            print_success("  - hsn_code field exists in Product model")
        else:
            print_error("  - hsn_code field MISSING from Product model")
            checks.append(False)
            
        if hasattr(Product, 'discount_percentage'):
            print_success("  - discount_percentage field exists in Product model")
        else:
            print_error("  - discount_percentage field MISSING from Product model")
            checks.append(False)
            
        checks.append(True)
    except Exception as e:
        print_error(f"Models import failed: {e}")
        checks.append(False)
    
    # Test Main App
    try:
        from app.main import app
        print_success("Main app imports successfully")
        
        # Check if ca_export router is registered
        router_paths = []
        for route in app.routes:
            if hasattr(route, 'path'):
                router_paths.append(route.path)
        
        ca_routes = [p for p in router_paths if '/ca-export' in p]
        if ca_routes:
            print_success(f"  - CA Export routes registered: {len(ca_routes)} endpoints")
        else:
            print_warning("  - CA Export routes not found (router may not be included)")
            
        checks.append(True)
    except Exception as e:
        print_error(f"Main app import failed: {e}")
        checks.append(False)
    
    return all(checks)

def check_dependencies():
    """Check if required dependencies are installed"""
    print("\n" + "="*70)
    print("CHECKING DEPENDENCIES")
    print("="*70)
    
    checks = []
    
    dependencies = [
        ('openpyxl', 'Excel generation'),
        ('fastapi', 'API framework'),
        ('sqlalchemy', 'Database ORM'),
        ('pydantic', 'Data validation'),
    ]
    
    for module, purpose in dependencies:
        try:
            __import__(module)
            print_success(f"{module} installed ({purpose})")
            checks.append(True)
        except ImportError:
            print_error(f"{module} NOT installed ({purpose})")
            checks.append(False)
    
    return all(checks)

def check_database():
    """Check database schema"""
    print("\n" + "="*70)
    print("CHECKING DATABASE SCHEMA")
    print("="*70)
    
    checks = []
    
    try:
        from app.database.connection import engine
        from sqlalchemy import text
        
        with engine.connect() as conn:
            # Check if products table exists
            result = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='products'"))
            if result.fetchone():
                print_success("products table exists")
                checks.append(True)
            else:
                print_error("products table does NOT exist")
                checks.append(False)
                return False
            
            # Check products table columns
            result = conn.execute(text("PRAGMA table_info(products)"))
            columns = [row[1] for row in result.fetchall()]
            
            print_info(f"Found {len(columns)} columns in products table")
            
            if 'hsn_code' in columns:
                print_success("  - hsn_code column exists")
                checks.append(True)
            else:
                print_error("  - hsn_code column MISSING (migration not applied)")
                checks.append(False)
            
            if 'discount_percentage' in columns:
                print_success("  - discount_percentage column exists")
                checks.append(True)
            else:
                print_error("  - discount_percentage column MISSING (migration not applied)")
                checks.append(False)
            
            # Check if migration record exists
            result = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='app_migrations'"))
            if result.fetchone():
                result = conn.execute(text("SELECT version FROM app_migrations WHERE version='008_hsn_and_discount_fields'"))
                if result.fetchone():
                    print_success("Migration 008 recorded in database")
                    checks.append(True)
                else:
                    print_warning("Migration 008 NOT recorded (may need to run)")
                    checks.append(True)  # Not critical
            else:
                print_warning("app_migrations table doesn't exist yet")
                checks.append(True)  # Not critical on first run
    
    except Exception as e:
        print_error(f"Database check failed: {e}")
        checks.append(False)
    
    return all(checks)

def check_files():
    """Check if all required files exist"""
    print("\n" + "="*70)
    print("CHECKING FILES")
    print("="*70)
    
    checks = []
    
    files = [
        ('app/routers/ca_export.py', 'CA Export Router'),
        ('app/models.py', 'Database Models'),
        ('app/schemas.py', 'Pydantic Schemas'),
        ('app/main.py', 'Main Application'),
        ('app/database/migrations.py', 'Database Migrations'),
        ('../CA_EXPORT_IMPLEMENTATION.md', 'Technical Documentation'),
        ('../DATABASE_AND_CA_EXPORT_SUMMARY.md', 'User Guide'),
        ('../TEST_CA_EXPORT.md', 'Testing Guide'),
        ('../QUICK_START_CA_EXPORT.md', 'Quick Start Guide'),
    ]
    
    for filepath, description in files:
        full_path = os.path.join(os.path.dirname(__file__), 'backend', filepath)
        if os.path.exists(full_path):
            size_kb = os.path.getsize(full_path) / 1024
            print_success(f"{description} exists ({size_kb:.1f} KB)")
            checks.append(True)
        else:
            print_error(f"{description} NOT FOUND at {filepath}")
            checks.append(False)
    
    return all(checks)

def check_api_endpoints():
    """Check if API endpoints are properly configured"""
    print("\n" + "="*70)
    print("CHECKING API ENDPOINTS")
    print("="*70)
    
    try:
        from app.routers.ca_export import router
        
        routes = []
        for route in router.routes:
            if hasattr(route, 'path') and hasattr(route, 'methods'):
                routes.append((route.path, list(route.methods)))
        
        if routes:
            print_success(f"Found {len(routes)} CA Export endpoints:")
            for path, methods in routes:
                print_info(f"  - {methods[0]} {path}")
            return True
        else:
            print_error("No CA Export endpoints found")
            return False
    
    except Exception as e:
        print_error(f"API endpoint check failed: {e}")
        return False

def print_summary(results):
    """Print final summary"""
    print("\n" + "="*70)
    print("VERIFICATION SUMMARY")
    print("="*70)
    
    total = len(results)
    passed = sum(results.values())
    
    for check, result in results.items():
        if result:
            print_success(check)
        else:
            print_error(check)
    
    print("\n" + "-"*70)
    if passed == total:
        print(f"{GREEN}✅ ALL CHECKS PASSED ({passed}/{total}){RESET}")
        print(f"{GREEN}🎉 Implementation is ready to test!{RESET}")
        print(f"\n{BLUE}Next Steps:{RESET}")
        print("1. Start the backend: cd backend && venv\\Scripts\\activate && python -m uvicorn app.main:app --reload")
        print("2. Visit http://localhost:8765/docs to see API documentation")
        print("3. Follow QUICK_START_CA_EXPORT.md for testing")
        return 0
    else:
        print(f"{RED}❌ {total - passed} CHECK(S) FAILED ({passed}/{total} passed){RESET}")
        print(f"\n{YELLOW}Issues Found:{RESET}")
        for check, result in results.items():
            if not result:
                print(f"  - {check}")
        print(f"\n{BLUE}Recommended Actions:{RESET}")
        print("1. Check error messages above")
        print("2. Ensure venv is activated")
        print("3. Run: pip install -r backend/requirements.txt")
        print("4. Run: cd backend && python -c 'from app.database.migrations import initialize_database; initialize_database()'")
        return 1

def main():
    """Main verification function"""
    print(f"\n{BLUE}{'='*70}{RESET}")
    print(f"{BLUE}CA EXPORT IMPLEMENTATION VERIFICATION{RESET}")
    print(f"{BLUE}{'='*70}{RESET}")
    
    # Change to backend directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    backend_dir = os.path.join(script_dir, 'backend')
    
    if os.path.exists(backend_dir):
        os.chdir(backend_dir)
        print_info(f"Working directory: {backend_dir}")
    else:
        print_error(f"Backend directory not found: {backend_dir}")
        return 1
    
    results = {}
    
    # Run all checks
    results['Dependencies'] = check_dependencies()
    results['Module Imports'] = check_imports()
    results['Database Schema'] = check_database()
    results['Required Files'] = check_files()
    results['API Endpoints'] = check_api_endpoints()
    
    # Print summary
    return print_summary(results)

if __name__ == '__main__':
    sys.exit(main())
