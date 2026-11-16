"""
Check OpenAPI schema to see if routes are registered
"""
import sys
import os
import json

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from app.main import app

print("=== Checking OpenAPI Schema ===\n")

openapi = app.openapi()

print(f"API Title: {openapi.get('info', {}).get('title')}")
print(f"API Version: {openapi.get('info', {}).get('version')}")

paths = openapi.get('paths', {})
print(f"\nTotal paths in OpenAPI: {len(paths)}")

# Categorize paths
api_paths = {}
system_paths = {}

for path, methods in paths.items():
    if any(prefix in path for prefix in ['/auth', '/products', '/farmers', '/billing', '/dashboard', '/outstanding', '/reports', '/notifications', '/ca-export']):
        api_paths[path] = list(methods.keys())
    else:
        system_paths[path] = list(methods.keys())

print(f"\nAPI paths: {len(api_paths)}")
print(f"System paths: {len(system_paths)}")

if api_paths:
    print("\n✓ API Endpoints Found:")
    for path in sorted(api_paths.keys()):
        methods_str = ', '.join(m.upper() for m in api_paths[path] if m != 'parameters')
        print(f"  {methods_str:20} {path}")
else:
    print("\n✗ NO API ENDPOINTS FOUND IN OPENAPI!")
    print("\nThis means the routers are NOT being included in the FastAPI app.")
    print("\nSystem paths found:")
    for path in sorted(system_paths.keys()):
        methods_str = ', '.join(m.upper() for m in system_paths[path] if m != 'parameters')
        print(f"  {methods_str:20} {path}")
