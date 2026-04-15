import json
import click
from flask.cli import with_appcontext
from werkzeug.security import generate_password_hash
from . import db


@click.command('init-db')
@with_appcontext
def init_db_command():
    """Create tables and seed default data."""
    from flask import current_app
    from .models import User, Item

    db.create_all()

    # ── Admin user ──────────────────────────────────────────
    if not User.query.filter_by(username='admin').first():
        admin_pwd = current_app.config.get('ADMIN_PASSWORD', 'admin123')
        admin = User(
            username='admin',
            password_hash=generate_password_hash(admin_pwd),
            full_name='Administrator',
            is_admin=True,
        )
        db.session.add(admin)
        db.session.commit()
        click.echo(f'Admin user created: admin / {admin_pwd}')
    else:
        click.echo('Admin user already exists, skipping.')

    # ── Default IEEMA transformer item ───────────────────────
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
        click.echo('Seeded default item: Main Transformer 6531 KVA')

    # ── Default IGBT item ─────────────────────────────────────
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
        click.echo('Seeded default IGBT item: IGBT Propulsion System')

    click.echo('Database initialised successfully.')


def register_cli(app):
    app.cli.add_command(init_db_command)
