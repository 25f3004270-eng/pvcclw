"""
Authentication routes: register, login, logout.

TODO: Copy route handlers from original app.py lines ~690-770:
- @app.route('/register', methods=['GET', 'POST'])
- @app.route('/login', methods=['GET', 'POST'])
- @app.route('/logout')
and paste them below, changing @app.route to @auth_bp.route
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash

from .. import db
from ..models import User

auth_bp = Blueprint('auth', __name__)

# user_loader must be in app/__init__.py or here with login_manager import
from .. import login_manager

@login_manager.user_loader
def load_user(uid):
    return db.session.get(User, int(uid))


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    # TODO: copy register logic from original app.py
    pass


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    # TODO: copy login logic from original app.py
    pass


@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth.login'))
