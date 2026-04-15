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

    # ── Config ────────────────────────────────────────────────
    secret = os.environ.get('SECRET_KEY', 'fallback-secret-key')
    app.config['SECRET_KEY'] = secret

    DATABASE_URL = (
        os.environ.get('DATABASE_URL')
        or 'mysql+pymysql://root:@localhost/pvc_db'
    )
    app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # ── Extensions ────────────────────────────────────────────
    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)

    # ── Models (must import after db init) ────────────────────
    from . import models  # noqa: F401

    # ── Blueprints ────────────────────────────────────────────
    from .routes.auth import auth_bp
    from .routes.calculator import calc_bp
    from .routes.admin import admin_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(calc_bp)
    app.register_blueprint(admin_bp, url_prefix='/admin')

    # ── CLI commands ──────────────────────────────────────────
    from .cli import register_cli
    register_cli(app)

    return app
