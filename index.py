import sys
import os

# Ensure root directory is in sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app as _flask_app

# WSGI handler for Vercel Serverless
def app(environ, start_response):
    # Check if Vercel provided the original rewritten request path
    matched_path = (
        environ.get('HTTP_X_MATCHED_PATH', '') 
        or environ.get('HTTP_X_VERCEL_MATCHED_PATH', '')
    )
    if matched_path:
        environ['PATH_INFO'] = matched_path.split('?')[0]

    path = environ.get('PATH_INFO', '')
    if path in ('/api/index.py', '/api/index', '/api', ''):
        environ['PATH_INFO'] = '/'

    return _flask_app(environ, start_response)

handler = app
