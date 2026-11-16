"""
Quick test to verify backend configuration
"""
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

print("=== Testing Backend Configuration ===\n")

try:
    from app.main import app
    print("✓ Main app imported successfully")
    
    # Check registered routes
    routes = []
    api_routes = []
    for route in app.routes:
        if hasattr(route, 'path'):
            if hasattr(route, 'methods'):
                methods = ','.join(route.methods) if route.methods else 'N/A'
            else:
                methods = 'MOUNT' if hasattr(route, 'app') else 'OTHER'
            route_str = f"{methods:10} {route.path}"
            routes.append(route_str)
            if any(prefix in route.path for prefix in ['/auth', '/products', '/farmers', '/billing', '/dashboard', '/outstanding', '/reports', '/notifications', '/ca-export']):
                api_routes.append(route_str)
    
    print(f"\n✓ Found {len(routes)} total routes")
    print(f"✓ Found {len(api_routes)} API routes")
    
    if len(api_routes) == 0:
        print("\n⚠ WARNING: No API routes found! The routers may not be properly included.")
    
    print("\nAll Routes:")
    for route in sorted(routes):
        print(f"  {route}")
    
    # Check routers
    print("\n=== Router Verification ===")
    from app.routers import auth, products, farmers, billing, dashboard, outstanding, reports, notifications, ca_export
    print("✓ All routers imported successfully")
    print(f"  - auth router prefix: {auth.router.prefix}")
    print(f"  - products router prefix: {products.router.prefix}")
    print(f"  - ca_export router prefix: {ca_export.router.prefix}")
    
    # Check database
    print("\n=== Database Check ===")
    from app.database import get_db
    from app.models import Product
    from sqlalchemy import func
    
    db = next(get_db())
    product_count = db.query(func.count(Product.id)).scalar()
    print(f"✓ Database connected")
    print(f"✓ Products in database: {product_count}")
    
    products_with_hsn = db.query(func.count(Product.id)).filter(Product.hsn_code.isnot(None)).scalar()
    print(f"✓ Products with HSN codes: {products_with_hsn}")
    
    print("\n=== All Tests Passed ===")
    
except ImportError as e:
    print(f"✗ Import error: {e}")
    sys.exit(1)
except Exception as e:
    print(f"✗ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
