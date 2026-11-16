#!/usr/bin/env python3
"""
Verification script for UI Redesign
Checks that all files are in place and properly linked
"""

import os
import re
from pathlib import Path

def check_mark(success):
    return "✓" if success else "✗"

def main():
    print("=" * 80)
    print("ADINATH AGRI SERVICES - UI REDESIGN VERIFICATION")
    print("=" * 80)
    print()
    
    checks_passed = 0
    total_checks = 0
    
    # Check 1: redesign.css exists
    total_checks += 1
    redesign_css_path = Path("frontend/css/redesign.css")
    redesign_exists = redesign_css_path.exists()
    print(f"[{check_mark(redesign_exists)}] Check 1: redesign.css exists")
    if redesign_exists:
        checks_passed += 1
        size = redesign_css_path.stat().st_size
        lines = len(redesign_css_path.read_text(encoding='utf-8').splitlines())
        print(f"    → Size: {size:,} bytes, Lines: {lines:,}")
    
    # Check 2: index.html exists
    total_checks += 1
    index_html_path = Path("frontend/index.html")
    index_exists = index_html_path.exists()
    print(f"[{check_mark(index_exists)}] Check 2: index.html exists")
    if index_exists:
        checks_passed += 1
    
    # Check 3: index.html links to redesign.css
    total_checks += 1
    redesign_linked = False
    if index_exists:
        html_content = index_html_path.read_text(encoding='utf-8')
        redesign_linked = 'redesign.css' in html_content
        print(f"[{check_mark(redesign_linked)}] Check 3: index.html links to redesign.css")
        if redesign_linked:
            checks_passed += 1
            # Extract the CSS link
            match = re.search(r'<link[^>]*href="[^"]*redesign\.css[^"]*"[^>]*>', html_content)
            if match:
                print(f"    → {match.group(0)}")
    
    # Check 4: Old CSS files backed up
    total_checks += 1
    style_css_path = Path("frontend/css/style.css")
    enhanced_css_path = Path("frontend/css/enhanced.css")
    backups_exist = style_css_path.exists() and enhanced_css_path.exists()
    print(f"[{check_mark(backups_exist)}] Check 4: Old CSS files preserved (style.css, enhanced.css)")
    if backups_exist:
        checks_passed += 1
    
    # Check 5: Backend running
    total_checks += 1
    import subprocess
    try:
        result = subprocess.run(
            ["powershell", "-Command", "Get-Process | Where-Object {$_.Path -like '*uvicorn*'} | Select-Object -First 1"],
            capture_output=True,
            text=True,
            timeout=5
        )
        backend_running = result.stdout.strip() != ""
    except:
        backend_running = False
    
    print(f"[{check_mark(backend_running)}] Check 5: Backend server running")
    if backend_running:
        checks_passed += 1
        print("    → Backend is running on http://localhost:8000")
    else:
        print("    → Start backend with: .\\backend\\venv\\Scripts\\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000")
    
    # Check 6: Database exists
    total_checks += 1
    db_path = Path("backend/adinath.db")
    db_exists = db_path.exists()
    print(f"[{check_mark(db_exists)}] Check 6: Database exists (adinath.db)")
    if db_exists:
        checks_passed += 1
        size = db_path.stat().st_size
        print(f"    → Size: {size:,} bytes")
    
    # Summary
    print()
    print("=" * 80)
    print(f"RESULTS: {checks_passed}/{total_checks} checks passed")
    print("=" * 80)
    
    if checks_passed == total_checks:
        print()
        print("✅ ALL CHECKS PASSED!")
        print()
        print("Your UI redesign is ready to test:")
        print("→ Open http://localhost:8000 in your browser")
        print("→ Login with: admin / admin123")
        print("→ Test the Add Customer button (was previously broken)")
        print()
    else:
        print()
        print("⚠️ Some checks failed. Please review the output above.")
        print()
    
    return checks_passed == total_checks

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
