"""
Calculator routes: index, calculate, history, viewcalc, export.

TODO: Copy from original app.py lines ~780-900:
- @app.route('/')  -> index
- @app.route('/calculate', methods=['POST'])
- @app.route('/history')
- @app.route('/calc/<calcid>')
- @app.route('/calc/<calcid>/excel')
- @app.route('/get_tender/<tenderid>')

Change @app.route to @calc_bp.route
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, send_file, jsonify
from flask_login import login_required, current_user
import json
import pandas as pd
from io import BytesIO

from .. import db
from ..models import Item, TenderMaster, PVCResult
from ..services.helpers import PVCInput, get_item_index_df
from ..services.pvc_ieema import calc_single_record
from ..services.pvc_igbt import calculate_igbt_propulsion

calc_bp = Blueprint('calculator', __name__)


class ResultObj:
    """Wrapper for result dict used in templates."""
    def __init__(self, payload):
        self.data = payload
        self.scenarioamounts      = payload.get('scenarioamounts', {})
        self.scenariodetails      = payload.get('scenariodetails', [])
        self.igbt_vendor_details  = payload.get('igbt_vendor_details', [])
        self.igbt_index_details   = payload.get('igbt_index_details', [])


@calc_bp.route('/')
@login_required
def index():
    # TODO: copy from app.py
    pass


@calc_bp.route('/calculate', methods=['POST'])
@login_required
def calculate():
    # TODO: copy from app.py; change calc_single_record and calculate_igbt_propulsion imports
    pass


@calc_bp.route('/history')
@login_required
def history():
    pass


@calc_bp.route('/calc/<int:calcid>')
@login_required
def viewcalc(calcid):
    pass


@calc_bp.route('/calc/<int:calcid>/excel')
@login_required
def exportcalcexcel(calcid):
    pass


@calc_bp.route('/get_tender/<int:tenderid>')
@login_required
def gettender(tenderid):
    pass
