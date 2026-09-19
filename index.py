import sys
import os

# Ensure root directory is in sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app as _flask_app

# WSGI handler that fixes Vercel serverless PATH_INFO routing
def app(environ, start_response):
    path = environ.get('PATH_INFO', '')
    if path.startswith('/api/index.py'):
        environ['PATH_INFO'] = path[len('/api/index.py'):] or '/'
    elif path.startswith('/api/index'):
        environ['PATH_INFO'] = path[len('/api/index'):] or '/'
    elif path.startswith('/api'):
        environ['PATH_INFO'] = path[len('/api'):] or '/'
    return _flask_app(environ, start_response)
