#!/usr/bin/env python
"""
CSRF Error Troubleshooting Script
=================================

This script helps diagnose and fix CSRF (Cross-Site Request Forgery) verification failures
in Django applications.

Usage:
    python csrf_fix.py

What this script does:
1. Checks Django settings for CSRF configuration
2. Tests CSRF token generation
3. Provides solutions for common CSRF issues
4. Validates session configuration
"""

import os
import sys
import django

def setup_django():
    """Setup Django environment"""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ml_backend.settings')
    try:
        django.setup()
        print("✅ Django environment loaded successfully")
        return True
    except Exception as e:
        print(f"❌ Failed to load Django: {e}")
        return False

def check_csrf_settings():
    """Check CSRF-related settings"""
    from django.conf import settings
    
    print("\n🔍 CHECKING CSRF SETTINGS:")
    print("=" * 50)
    
    # Check DEBUG mode
    debug_mode = getattr(settings, 'DEBUG', False)
    print(f"DEBUG mode: {debug_mode}")
    if debug_mode:
        print("  ⚠️  You're in DEBUG mode - CSRF is more lenient")
    
    # Check CSRF settings
    csrf_settings = [
        'CSRF_COOKIE_SECURE',
        'CSRF_COOKIE_HTTPONLY', 
        'CSRF_COOKIE_SAMESITE',
        'CSRF_TRUSTED_ORIGINS',
        'CSRF_FAILURE_VIEW',
    ]
    
    for setting in csrf_settings:
        value = getattr(settings, setting, 'NOT SET')
        print(f"{setting}: {value}")
    
    # Check middleware order
    middleware = getattr(settings, 'MIDDLEWARE', [])
    print(f"\n📋 MIDDLEWARE ORDER:")
    for i, mw in enumerate(middleware, 1):
        marker = ""
        if 'csrf' in mw.lower():
            marker = " 🎯 CSRF"
        elif 'session' in mw.lower():
            marker = " 📦 SESSION"
        elif 'cors' in mw.lower():
            marker = " 🌐 CORS"
        print(f"  {i}. {mw}{marker}")
    
    # Check session configuration
    session_settings = [
        'SESSION_COOKIE_SECURE',
        'SESSION_COOKIE_HTTPONLY',
        'SESSION_COOKIE_SAMESITE',
        'SESSION_ENGINE',
    ]
    
    print(f"\n🍪 SESSION SETTINGS:")
    for setting in session_settings:
        value = getattr(settings, setting, 'NOT SET')
        print(f"{setting}: {value}")

def test_csrf_token_generation():
    """Test CSRF token generation"""
    print("\n🧪 TESTING CSRF TOKEN GENERATION:")
    print("=" * 50)
    
    try:
        from django.middleware.csrf import get_token
        from django.test import RequestFactory
        from django.contrib.sessions.middleware import SessionMiddleware
        
        # Create a test request
        factory = RequestFactory()
        request = factory.get('/')
        
        # Process session middleware
        middleware = SessionMiddleware()
        middleware.process_request(request)
        request.session.save()
        
        # Generate CSRF token
        token = get_token(request)
        print(f"✅ CSRF token generated: {token[:10]}...")
        print(f"✅ Session key: {request.session.session_key}")
        
        return True
        
    except Exception as e:
        print(f"❌ Failed to generate CSRF token: {e}")
        return False

def check_cors_configuration():
    """Check CORS configuration that might interfere with CSRF"""
    from django.conf import settings
    
    print("\n🌐 CHECKING CORS CONFIGURATION:")
    print("=" * 50)
    
    cors_settings = [
        'CORS_ALLOWED_ORIGINS',
        'CORS_ALLOW_CREDENTIALS',
        'CORS_ALLOW_ALL_ORIGINS',
        'CORS_ALLOWED_HEADERS',
    ]
    
    for setting in cors_settings:
        value = getattr(settings, setting, 'NOT SET')
        print(f"{setting}: {value}")
        
        if setting == 'CORS_ALLOW_ALL_ORIGINS' and value is True:
            print("  ⚠️  CORS_ALLOW_ALL_ORIGINS=True can interfere with CSRF!")

def provide_solutions():
    """Provide common solutions for CSRF issues"""
    print("\n💡 COMMON CSRF SOLUTIONS:")
    print("=" * 50)
    
    solutions = [
        {
            "issue": "CSRF token missing from POST",
            "solution": "Ensure {% csrf_token %} is in your forms",
            "code": '<form method="post">\n    {% csrf_token %}\n    <!-- form fields -->\n</form>'
        },
        {
            "issue": "CORS interfering with CSRF",
            "solution": "Set CORS_ALLOW_ALL_ORIGINS=False and use specific origins",
            "code": "CORS_ALLOWED_ORIGINS = ['http://localhost:8000']\nCORS_ALLOW_ALL_ORIGINS = False"
        },
        {
            "issue": "AJAX requests failing CSRF",
            "solution": "Include CSRF token in AJAX headers",
            "code": "headers: {\n    'X-CSRFToken': getCookie('csrftoken')\n}"
        },
        {
            "issue": "Session not persisting",
            "solution": "Check session middleware and database",
            "code": "SESSION_COOKIE_HTTPONLY = True\nSESSION_COOKIE_SAMESITE = 'Lax'"
        }
    ]
    
    for i, solution in enumerate(solutions, 1):
        print(f"\n{i}. {solution['issue']}")
        print(f"   Solution: {solution['solution']}")
        print(f"   Code:")
        for line in solution['code'].split('\n'):
            print(f"     {line}")

def run_diagnostics():
    """Run full CSRF diagnostics"""
    print("🔧 CSRF ERROR DIAGNOSTIC TOOL")
    print("=" * 50)
    
    if not setup_django():
        return False
    
    check_csrf_settings()
    test_csrf_token_generation()
    check_cors_configuration()
    provide_solutions()
    
    print("\n🎯 NEXT STEPS:")
    print("=" * 20)
    print("1. Visit http://localhost:8000/api/ml/debug/csrf-test/ to test CSRF")
    print("2. Check your browser's developer tools for CSRF cookie")
    print("3. Ensure your forms include {% csrf_token %}")
    print("4. Review CORS settings if using frontend frameworks")
    print("5. Check Django logs for specific CSRF errors")
    
    return True

if __name__ == "__main__":
    success = run_diagnostics()
    sys.exit(0 if success else 1)
