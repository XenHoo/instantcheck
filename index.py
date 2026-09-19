import sys
import os

# Ensure root directory is in sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app as _flask_app

# WSGI handler for Vercel Serverless
def app(environ, start_response):
    # Retrieve original path from all possible Vercel headers
    matched_path = (
        environ.get('HTTP_X_MATCHED_PATH')
        or environ.get('HTTP_X_VERCEL_MATCHED_PATH')
        or environ.get('HTTP_X_FORWARDED_URI')
        or environ.get('HTTP_X_ORIGINAL_URL')
        or environ.get('RAW_URI')
        or environ.get('REQUEST_URI')
        or ''
    )
    if matched_path:
        clean_path = matched_path.split('?')[0].strip()
        if clean_path and clean_path not in ('/api/index.py', '/api/index', '/api'):
            environ['PATH_INFO'] = clean_path

    path = environ.get('PATH_INFO', '')
    if path in ('/api/index.py', '/api/index', '/api', ''):
        environ['PATH_INFO'] = '/'

    return _flask_app(environ, start_response)

handler = app
