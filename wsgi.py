#!/usr/bin/env python3
"""WSGI entry point - uses monolithic app.py until blueprint migration completes."""
import os
import sys

# Fix Render postgres:// -> postgresql:// (SQLAlchemy requirement)
db_url = os.environ.get('DATABASE_URL', '')
if db_url.startswith('postgres://'):
    os.environ['DATABASE_URL'] = db_url.replace('postgres://', 'postgresql://', 1)

# Import app from monolithic app.py (not from blueprinted app/ package)
try:
    # Attempt to import from app package (blueprinted structure)
    from app import create_app
    app = create_app()
    print('[wsgi] Using blueprinted app structure', file=sys.stderr)
except (ImportError, AttributeError) as e:
    # Fall back to monolithic app.py
    print(f'[wsgi] Blueprint import failed ({e}), using monolithic app.py', file=sys.stderr)
    import app as app_module
    app = app_module.app

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_DEBUG', 'false').lower() == 'true'
    app.run(host='0.0.0.0', port=port, debug=debug)
