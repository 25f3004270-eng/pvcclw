import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect

db = SQLAlchemy()
login_manager = LoginManager()
login_manager.login_view = 'auth.login'
csrf = CSRFProtect()


def create_app():
    app = Flask(__name__, template_folder='../templates')

    # ── Config ──────────────────────────────────────────────────
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'fallback-secret-key')

    # Fix Render postgres:// -> postgresql:// (SQLAlchemy requirement)
    raw_db_url = os.environ.get('DATABASE_URL', '')
    if raw_db_url.startswith('postgres://'):
        raw_db_url = raw_db_url.replace('postgres://', 'postgresql://', 1)

    DATABASE_URL = raw_db_url or 'sqlite:///pvc_db.sqlite3'
    app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['WTF_CSRF_ENABLED'] = True

    # ── Extensions ───────────────────────────────────────────────
    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)

    # ── Models (must import after db init) ───────────────────────
    from . import models  # noqa: F401

    # ── DB init + seed ───────────────────────────────────────────
    with app.app_context():
        db.create_all()
        _seed_defaults()

    # ── Blueprints ───────────────────────────────────────────────
    from .routes.auth import auth_bp
    from .routes.calculator import calc_bp
    from .routes.admin import admin_bp
    app.register_blueprint(auth_bp)
    app.register_blueprint(calc_bp)
    app.register_blueprint(admin_bp, url_prefix='/admin')

    # ── CLI commands ─────────────────────────────────────────────
    from .cli import register_cli
    register_cli(app)

    return app


def _seed_defaults():
    import json
    from .models import User, Item
    from werkzeug.security import generate_password_hash

    if not User.query.filter_by(username='admin').first():
        admin = User(
            username='admin',
            password_hash=generate_password_hash(
                os.environ.get('ADMIN_PASSWORD', 'admin123')
            ),
            full_name='Administrator',
            is_admin=True,
        )
        db.session.add(admin)
        db.session.commit()

    if Item.query.count() == 0:
        default_weights = {
            'copper': 40, 'crgo': 24, 'ms': 8,
            'insmat': 4, 'transoil': 8, 'wpi': 8,
        }
        itm = Item(
            name='Main Transformer 6531 KVA (PL NO: 29721008)',
            code='TRANSFORMER_6531',
            pvc_formula_code='POWERTRFIEEMA',
            weights_json=json.dumps(default_weights),
            extra_fields_json='[]',
            description='Default transformer - IEEMA PVC formula.',
        )
        db.session.add(itm)
        db.session.commit()

    igbt_exists = Item.query.filter(
        Item.pvc_formula_code.ilike('%IGBT%')
    ).first()
    if not igbt_exists:
        igbt_weights = {
            'FIXED': 16, 'C': 26, 'AL': 13,
            'FE': 18, 'IM': 9, 'W': 18,
        }
        igbt_item = Item(
            name='IGBT Propulsion System',
            code='IGBT_PROP',
            pvc_formula_code='IGBTPROPULSIONSYSTEM',
            weights_json=json.dumps(igbt_weights),
            extra_fields_json='[]',
            description='IGBT Propulsion - P1/P2 vendor-wise PVC formula.',
        )
        db.session.add(igbt_item)
        db.session.commit()
