"""
Admin routes: tenders, vendors, items, item indices.

TODO: Copy from original app.py lines ~920-1200:
- admin_required decorator
- Tender CRUD routes
- Tender Vendor CRUD routes
- Item CRUD routes
- ItemIndex CRUD routes

Change @app.route to @admin_bp.route and add url_prefix='/admin' in blueprint registration.
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, abort
from flask_login import login_required, current_user
from functools import wraps
import json
from datetime import datetime, date

from .. import db
from ..models import Item, ItemIndex, TenderMaster, TenderVendor
from ..services.helpers import safe_float, invalidate_index_cache

admin_bp = Blueprint('admin', __name__)


def admin_required(fn):
    @wraps(fn)
    def wrapper(*a, **kw):
        if not current_user.is_authenticated:
            return abort(401)
        if not getattr(current_user, 'is_admin', False):
            abort(403)
        return fn(*a, **kw)
    return wrapper


# TODO: Copy all admin routes from app.py:
# /admin/tenders, /admin/tenders/new, /admin/tenders/<id>/edit
# /admin/tenders/<id>/vendors, /admin/tenders/<id>/vendors/new, /admin/tenders/<id>/vendors/<vid>/edit
# /admin/items, /admin/items/new, /admin/items/<id>/edit
# /admin/items/<id>/indices, /admin/items/<id>/indices/new, /admin/items/<id>/indices/<rowid>/edit
