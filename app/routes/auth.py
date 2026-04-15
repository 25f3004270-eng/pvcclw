from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required
from werkzeug.security import generate_password_hash, check_password_hash

from .. import db, login_manager
from ..models import User

auth_bp = Blueprint('auth', __name__)


@login_manager.user_loader
def load_user(uid):
    return db.session.get(User, int(uid))


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = (request.form.get('username') or '').strip()
        password = (request.form.get('password') or '')
        full_name = (request.form.get('fullname') or '').strip()
        email = (request.form.get('email') or '').strip()
        contact_no = (request.form.get('contactno') or '').strip()
        designation = (request.form.get('designation') or '').strip()
        control_no = (request.form.get('controlno') or '').strip()

        if not username or not password:
            flash('Username and password are required.', 'danger')
            return redirect(url_for('auth.register'))

        if User.query.filter_by(username=username).first():
            flash('Username already exists.', 'danger')
            return redirect(url_for('auth.register'))

        if email and User.query.filter_by(email=email).first():
            flash('Email already registered.', 'danger')
            return redirect(url_for('auth.register'))

        user = User(
            username=username,
            password_hash=generate_password_hash(password),
            full_name=full_name,
            email=email or None,
            contact_no=contact_no,
            designation=designation,
            control_no=control_no,
            is_admin=False,
        )
        db.session.add(user)
        db.session.commit()
        flash('Registration successful. Please login.', 'success')
        return redirect(url_for('auth.login'))
    return render_template('register.html')


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = (request.form.get('username') or '').strip()
        password = request.form.get('password') or ''
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            return redirect(url_for('calc.index'))
        flash('Invalid username or password.', 'danger')
    return render_template('login.html')


@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth.login'))
