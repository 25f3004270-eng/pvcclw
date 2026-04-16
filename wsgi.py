#!/usr/bin/env python3
"""WSGI entry point - uses monolithic app.py until blueprint migration completes."""
import os
import sys

# Fix Render postgres:// -> postgresql:// (SQLAlchemy requirement)
db_url = os.environ.get('DATABASE_URL', '')
if db_url.startswith('postgres://'):
    os.environ['DATABASE_URL'] = db_url.replace('postgres://', 'postgresql://', 1)

# Import app from monolithic app.py
try:
    from app import app
except ImportError as e:
    print(f'[wsgi] Failed to import app: {e}', file=sys.stderr)
    sys.exit(1)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_DEBUG', 'false').lower() == 'true'
    app.run(host='0.0.0.0', port=port, debug=debug)