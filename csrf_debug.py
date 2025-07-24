# CSRF Debug Helper
# Run this in Django shell to debug CSRF issues

from django.middleware.csrf import get_token
from django.test import RequestFactory
from django.contrib.sessions.models import Session

def debug_csrf():
    """Debug CSRF token generation and validation"""
    factory = RequestFactory()
    request = factory.get('/')
    
    # Create a session
    from django.contrib.sessions.middleware import SessionMiddleware
    middleware = SessionMiddleware()
    middleware.process_request(request)
    request.session.save()
    
    # Get CSRF token
    token = get_token(request)
    print(f"CSRF Token: {token}")
    print(f"Session Key: {request.session.session_key}")
    
    # Check session data
    session = Session.objects.get(session_key=request.session.session_key)
    print(f"Session Data: {session.get_decoded()}")
    
    return token

if __name__ == "__main__":
    debug_csrf()
