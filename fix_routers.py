"""
Fix the router registration issue
"""
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

print("=== Diagnosing Router Registration Issue ===\n")

from app.main import app
from app.routers import auth, products, farmers, billing, dashboard, outstanding, reports, notifications, ca_export

print("Step 1: Check initial routes")
print(f"Routes before manual include: {len([r for r in app.routes if hasattr(r, 'path')])}")

print("\nStep 2: Manually include routers")
try:
    routers_to_include = [
        ('auth', auth.router),
        ('products', products.router),
        ('farmers', farmers.router),
        ('billing', billing.router),
        ('dashboard', dashboard.router),
        ('outstanding', outstanding.router),
        ('reports', reports.router),
        ('notifications', notifications.router),
        ('ca_export', ca_export.router),
    ]
    
    for name, router in routers_to_include:
        try:
            print(f"  Including {name} router (prefix: {router.prefix})...", end='')
            app.include_router(router)
            print(" ✓")
        except Exception as e:
            print(f" ✗ Error: {e}")
            
except Exception as e:
    print(f"Fatal error: {e}")
    import traceback
    traceback.print_exc()

print(f"\nStep 3: Check routes after manual include")
routes = [r for r in app.routes if hasattr(r, 'path')]
print(f"Total routes: {len(routes)}")

api_routes = [r for r in routes if any(prefix in r.path for prefix in ['/auth', '/products', '/farmers', '/billing', '/dashboard', '/outstanding', '/reports', '/notifications', '/ca-export'])]
print(f"API routes: {len(api_routes)}")

if api_routes:
    print("\nAPI Routes found:")
    for route in api_routes[:10]:
        methods = ','.join(route.methods) if hasattr(route, 'methods') and route.methods else 'N/A'
        print(f"  {methods:10} {route.path}")
else:
    print("\n⚠ Still no API routes! This suggests a deeper issue.")

print("\nStep 4: Check if routers have routes")
for name, router in routers_to_include:
    route_count = len(router.routes) if hasattr(router, 'routes') else 0
    print(f"  {name}: {route_count} routes defined")
