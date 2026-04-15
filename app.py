#!/usr/bin/env python3
import os
import json
import math
from io import BytesIO
from datetime import datetime, date
from functools import wraps

import pandas as pd
from dateutil.relativedelta import relativedelta
from flask import (
    Flask, render_template, request, redirect,
    url_for, flash, send_file, abort, jsonify
)
from flask_sqlalchemy import SQLAlchemy
from flask_login import (
    LoginManager, login_user, logout_user,
    login_required, current_user, UserMixin
)
from werkzeug.security import generate_password_hash, check_password_hash

# ─────────────────────────────────────────────────────────────
# CONSTANTS
# ─────────────────────────────────────────────────────────────
GST_FACTOR = 1.18

# ─────────────────────────────────────────────────────────────
# APP + DB
# ─────────────────────────────────────────────────────────────
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'fallback-secret-key')
DATABASE_URL = (
    os.environ.get('DATABASE_URL')
    or 'mysql+pymysql://root:@localhost/pvc_db'
)
app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db           = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'


# ─────────────────────────────────────────────────────────────
# MODELS
# ─────────────────────────────────────────────────────────────
class User(UserMixin, db.Model):
    id            = db.Column(db.Integer, primary_key=True)
    username      = db.Column(db.String(80),  unique=True, nullable=False)
    full_name     = db.Column(db.String(200))
    email         = db.Column(db.String(200), unique=True)
    contact_no    = db.Column(db.String(20))
    designation   = db.Column(db.String(120))
    control_no    = db.Column(db.String(120))
    password_hash = db.Column(db.String(256), nullable=False)
    is_admin      = db.Column(db.Boolean, default=False, nullable=False)


class Item(db.Model):
    id                = db.Column(db.Integer, primary_key=True)
    name              = db.Column(db.String(200), unique=True, nullable=False)
    code              = db.Column(db.String(50),  unique=True)
    description       = db.Column(db.Text)
    pvc_formula_code  = db.Column(db.String(50),  nullable=False)
    weights_json      = db.Column(db.Text, default='{}')
    extra_fields_json = db.Column(db.Text, default='[]')

    @property
    def pvcformulacode(self):  return self.pvc_formula_code
    @property
    def weightsjson(self):     return self.weights_json
    @property
    def extrafieldsjson(self): return self.extra_fields_json


class ItemIndex(db.Model):
    id           = db.Column(db.Integer, primary_key=True)
    item_id      = db.Column(db.Integer, db.ForeignKey('item.id'), nullable=False)
    item         = db.relationship('Item')
    month        = db.Column(db.Date, nullable=False)
    indices_json = db.Column(db.Text, nullable=False)

    @property
    def itemid(self):      return self.item_id
    @property
    def indicesjson(self): return self.indices_json


class PVCResult(db.Model):
    id                       = db.Column(db.Integer, primary_key=True)
    user_id                  = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    user                     = db.relationship('User')
    item_id                  = db.Column(db.Integer, db.ForeignKey('item.id'), nullable=False)
    item                     = db.relationship('Item')
    username                 = db.Column(db.String(80))
    created_at               = db.Column(db.DateTime, default=datetime.utcnow)
    basicrate                = db.Column(db.Float)
    quantity                 = db.Column(db.Float)
    freightrateperunit       = db.Column(db.Float)
    pvcbasedate              = db.Column(db.String(10))
    origdp                   = db.Column(db.String(10))
    refixeddp                = db.Column(db.String(10))
    extendeddp               = db.Column(db.String(10))
    caldate                  = db.Column(db.String(10))
    supdate                  = db.Column(db.String(10))
    rateapplied              = db.Column(db.String(100))
    pvcactual                = db.Column(db.Float)
    pvccontractual           = db.Column(db.Float)
    loweractual              = db.Column(db.Float)
    lowercontractual         = db.Column(db.Float)
    ldamtactual              = db.Column(db.Float)
    ldamtcontractual         = db.Column(db.Float)
    fairprice                = db.Column(db.Float)
    selectedscenario         = db.Column(db.String(10))
    pvcactuallessldnew       = db.Column(db.Float)
    pvccontractuallessldnew  = db.Column(db.Float)
    loweractuallessld        = db.Column(db.Float)
    lowercontractuallessld   = db.Column(db.Float)
    delaydays                = db.Column(db.Integer)
    ldweeksnew               = db.Column(db.Integer)
    ldratepctnew             = db.Column(db.Float)
    ldapplicable             = db.Column(db.Boolean, default=False)
    pvcperseta2              = db.Column(db.Float)
    pvcpersetb2              = db.Column(db.Float)
    pvcpersetc1              = db.Column(db.Float)
    pvcpersetd1              = db.Column(db.Float)
    tenderno                 = db.Column(db.String(100))
    pono                     = db.Column(db.String(100))
    scenarioamounts_json     = db.Column(db.Text)
    scenariodetails_json     = db.Column(db.Text)
    igbt_vendor_details_json = db.Column(db.Text)

    @property
    def createdat(self): return self.created_at
    @property
    def itemid(self):    return self.item_id
    @property
    def userid(self):    return self.user_id


class TenderMaster(db.Model):
    id                = db.Column(db.Integer, primary_key=True)
    item_id           = db.Column(db.Integer, db.ForeignKey('item.id'), nullable=False)
    item              = db.relationship('Item')
    tender_no         = db.Column(db.String(100), unique=True, nullable=False)
    basicrate         = db.Column(db.Float, default=0)
    pvcbasedate       = db.Column(db.String(10))
    freightrateperunit= db.Column(db.Float)
    lowerrate         = db.Column(db.Float, default=0)
    lowerratebasedate = db.Column(db.String(10))
    lowerfreight      = db.Column(db.Float)
    created_at        = db.Column(db.DateTime, default=datetime.utcnow)

    @property
    def itemid(self):    return self.item_id
    @property
    def tenderno(self):  return self.tender_no
    @property
    def createdat(self): return self.created_at
    @property
    def pono(self):
        v = (TenderVendor.query
             .filter_by(tender_id=self.id)
             .order_by(TenderVendor.id)
             .first())
        return v.po_no if v else None


class TenderVendor(db.Model):
    id          = db.Column(db.Integer, primary_key=True)
    tender_id   = db.Column(db.Integer, db.ForeignKey('tender_master.id'), nullable=False)
    tender      = db.relationship('TenderMaster', backref='vendors')
    po_no       = db.Column(db.String(50))
    vendor_name = db.Column(db.String(200), nullable=False)
    cif         = db.Column(db.Float, default=0)
    currency    = db.Column(db.String(10), nullable=False)

    @property
    def tenderid(self):   return self.tender_id
    @property
    def pono(self):       return self.po_no
    @property
    def vendorname(self): return self.vendor_name


# ─────────────────────────────────────────────────────────────
# INPUT NORMALISER
# ─────────────────────────────────────────────────────────────
class PVCInput:
    _KNOWN = {
        'itemid','item_id','basicrate','quantity','freightrateperunit',
        'pvcbasedate','origdp','refixeddp','extendeddp','caldate','supdate',
        'lowerrate','lowerfreight','lowerbasicdate','rateapplied',
        'tenderid','tender_id'
    }

    def __init__(self, form):
        self.user_id  = None
        self.username = None
        self.item_id  = int(form.get('itemid') or form.get('item_id') or 0)
        self.basic_rate            = self._f(form.get('basicrate'))
        self.quantity              = self._f(form.get('quantity'))
        self.freight_rate_per_unit = self._f(form.get('freightrateperunit'))
        self.pvc_base_date   = form.get('pvcbasedate')
        self.original_dp     = form.get('origdp')
        self.refixed_dp      = form.get('refixeddp')
        self.extended_dp     = form.get('extendeddp')
        self.cal_date        = form.get('caldate')
        self.supply_date     = form.get('supdate')
        self.lower_rate      = self._f(form.get('lowerrate'))
        self.lower_freight   = self._f(form.get('lowerfreight'))
        self.lower_basic_date= form.get('lowerbasicdate')
        self.rate_applied    = form.get('rateapplied')
        self.tender_id       = form.get('tenderid') or form.get('tender_id')
        self.extra_data      = {
            k: form.get(k)
            for k in form.keys()
            if k not in self._KNOWN
        }

    @staticmethod
    def _f(v):
        try:    return float(str(v or 0).replace(',', '').strip())
        except: return 0.0

    def to_dict(self):
        d = {
            'basicrate':          self.basic_rate,
            'quantity':           self.quantity,
            'freightrateperunit': self.freight_rate_per_unit,
            'pvcbasedate':        self.pvc_base_date,
            'origdp':             self.original_dp,
            'refixeddp':          self.refixed_dp,
            'extendeddp':         self.extended_dp,
            'caldate':            self.cal_date,
            'supdate':            self.supply_date,
            'lowerrate':          self.lower_rate,
            'lowerfreight':       self.lower_freight,
            'lowerbasicdate':     self.lower_basic_date,
            'rateapplied':        self.rate_applied,
            'tenderid':           self.tender_id,
        }
        d.update(self.extra_data)
        return d


# ─────────────────────────────────────────────────────────────
# AUTH HELPERS
# ─────────────────────────────────────────────────────────────
@login_manager.user_loader
def load_user(uid):
    return db.session.get(User, int(uid))


def admin_required(fn):
    @wraps(fn)
    def wrapper(*a, **kw):
        if not current_user.is_authenticated:
            return login_manager.unauthorized()
        if not getattr(current_user, 'is_admin', False):
            abort(403)
        return fn(*a, **kw)
    return wrapper


# ─────────────────────────────────────────────────────────────
# NUMERIC HELPERS
# ─────────────────────────────────────────────────────────────
def safe_float(x):
    try:    return float(str(x or 0).replace(',', '').strip())
    except: return 0.0

def safe_round(x, n=2):
    try:    return round(float(x), n)
    except: return None

def to_month_start(d):
    if not d: return pd.NaT
    ts = pd.to_datetime(d, errors='coerce')
    if pd.isna(ts): return pd.NaT
    return pd.Timestamp(ts.year, ts.month, 1)

def previous_month(d):
    d = to_month_start(d)
    return pd.NaT if pd.isna(d) else d - relativedelta(months=1)


# ─────────────────────────────────────────────────────────────
# INDEX DATA LOADER
# ─────────────────────────────────────────────────────────────
def get_item_index_df(item):
    rows = (ItemIndex.query
            .filter_by(item_id=item.id)
            .order_by(ItemIndex.month.asc())
            .all())
    if not rows:
        return pd.DataFrame()
    data = []
    for r in rows:
        try:    idx = json.loads(r.indices_json or '{}')
        except: idx = {}
        row = {'date': pd.Timestamp(r.month.year, r.month.month, 1)}
        row.update(idx)
        data.append(row)
    df = pd.DataFrame(data)
    if df.empty:
        return df
    return df.set_index('date').sort_index()


def ieema_row(df, dt, previous=False):
    """Return latest index row on or before target month."""
    if df is None or df.empty: return None
    target = previous_month(dt) if previous else to_month_start(dt)
    if pd.isna(target): return None
    eligible = df[df.index <= target]
    return eligible.iloc[-1] if not eligible.empty else None


# ─────────────────────────────────────────────────────────────
# IEEMA PVC % – SCALAR
# ─────────────────────────────────────────────────────────────
def pvc_percent(base_date, current_date, idx_df, weights):
    base = ieema_row(idx_df, base_date, previous=False)
    curr = ieema_row(idx_df, current_date, previous=True)
    if base is None or curr is None:
        return 0.0
    total = 0.0
    for key, weight in weights.items():
        b = base.get(key)
        c = curr.get(key)
        if b not in (None, 0) and c is not None:
            total += float(weight) * ((float(c) - float(b)) / float(b))
    return total


# ─────────────────────────────────────────────────────────────
# IEEMA PVC % – DETAILED (index-wise breakdown)
# ─────────────────────────────────────────────────────────────
def pvc_percent_detailed(base_date, current_date, idx_df, scenario, weights):
    base = ieema_row(idx_df, base_date, previous=False)
    curr = ieema_row(idx_df, current_date, previous=True)
    if base is None or curr is None:
        return None
    row = {
        'scenario':    scenario,
        'basemonth':   base.name.isoformat() if hasattr(base.name, 'isoformat') else str(base.name),
        'currentmonth':curr.name.isoformat() if hasattr(curr.name, 'isoformat') else str(curr.name),
        'pvcpercent':  0.0,
    }
    total = 0.0
    for key, weight in weights.items():
        b = base.get(key)
        c = curr.get(key)
        contrib = None
        if b not in (None, 0) and c is not None:
            contrib = round(float(weight) * ((float(c) - float(b)) / float(b)), 4)
            total  += contrib
        row[f'{key}_base']            = safe_round(b, 2) if b is not None else None
        row[f'{key}_current']         = safe_round(c, 2) if c is not None else None
        row[f'{key}_weight']          = weight
        row[f'{key}_contributionpct'] = contrib
    row['pvcpercent'] = round(total, 4)
    return row


# ─────────────────────────────────────────────────────────────
# IGBT HELPERS – P1 / P2 / vendor-wise breakdown
# ─────────────────────────────────────────────────────────────
def _igbt_index_values(idx_df, month, currency):
    """
    Return dict of base or current index values needed for IGBT calc.
    Keys: C, AL, FE, IM, W, D, ER
    currency: e.g. 'EUR', 'USD', 'JPY'
    """
    currency = (currency or 'EUR').upper().strip()
    er_col   = f'ER_{currency}'

    row = ieema_row(idx_df, month, previous=False)
    if row is None:
        raise ValueError(f'IGBT indices missing for month {month}')

    def _get(col):
        v = row.get(col)
        if v is None:
            raise ValueError(f'Index column "{col}" missing for {month}')
        return float(v)

    return {
        'C':  _get('C'),
        'AL': _get('AL'),
        'FE': _get('FE'),
        'IM': _get('IM'),
        'W':  _get('W'),
        'D':  _get('D'),
        'ER': _get(er_col),
    }


def _igbt_p1(indigenous_value, base_idx, curr_idx, weights):
    """
    P1 = indigenous component PVC
    Formula (original RDSO/IGBT pattern):
      P1 = (Iv/100) * [Fc + wC*(C1/C0) + wAL*(AL1/AL0)
                       + wFE*(FE1/FE0) + wIM*(IM1/IM0) + wW*(W1/W0)] - Iv
    where Fc = fixed % (default 16), weights are % values summing to 84
    """
    Fc  = float(weights.get('FIXED', 16))
    wC  = float(weights.get('C',  26))
    wAL = float(weights.get('AL', 13))
    wFE = float(weights.get('FE', 18))
    wIM = float(weights.get('IM',  9))
    wW  = float(weights.get('W',  18))

    factor = (
        Fc
        + wC  * (curr_idx['C']  / base_idx['C'])
        + wAL * (curr_idx['AL'] / base_idx['AL'])
        + wFE * (curr_idx['FE'] / base_idx['FE'])
        + wIM * (curr_idx['IM'] / base_idx['IM'])
        + wW  * (curr_idx['W']  / base_idx['W'])
    )
    return (indigenous_value / 100.0) * factor - indigenous_value


def _igbt_p2(cif_value, base_idx, curr_idx):
    """
    P2 = imported component (CIF) PVC
    Formula:
      P2 = (CIF/100) * [(ER1/ER0)*(100+D1) - (100+D0)]
    """
    return (cif_value / 100.0) * (
        (curr_idx['ER'] / base_idx['ER']) * (100.0 + curr_idx['D'])
        - (100.0 + base_idx['D'])
    )


def _igbt_vendor_scenario(
    rate, vendor, base_month, ref_month, idx_df, weights, scenario_label
):
    """
    Compute P1+P2 for one vendor in one scenario.
    Returns (vendor_summary_dict, index_detail_list)
    """
    currency = (vendor.currency or 'EUR').upper()

    # base indices: use base_month WITHOUT previous-month shift (IEEMA base rule)
    base_idx = _igbt_index_values(idx_df, base_month, currency)

    # current indices: use previous month of ref_month (IEEMA current rule)
    curr_month = previous_month(ref_month)
    curr_idx   = _igbt_index_values(idx_df, curr_month, currency)

    cif         = safe_float(vendor.cif)
    base_duty   = cif * base_idx['D'] / 100.0
    indigenous  = rate - cif - base_duty      # indigenous portion

    p1 = _igbt_p1(indigenous, base_idx, curr_idx, weights)
    p2 = _igbt_p2(cif, base_idx, curr_idx)
    total_pvc = p1 + p2

    summary = {
        'scenario':    scenario_label,
        'vendor':      vendor.vendor_name,
        'pono':        vendor.po_no,
        'currency':    currency,
        'rate':        safe_round(rate),
        'cif':         safe_round(cif),
        'base_duty':   safe_round(base_duty),
        'indigenous':  safe_round(indigenous),
        'p1':          safe_round(p1),
        'p2':          safe_round(p2),
        'total_pvc':   safe_round(total_pvc),
        'basemonth':   str(base_month.date()) if hasattr(base_month, 'date') else str(base_month),
        'currentmonth':str(curr_month.date()) if hasattr(curr_month, 'date') else str(curr_month),
    }

    # index-wise detail rows (one row per index parameter)
    index_details = []
    params = [
        ('C',  'Copper Index'),
        ('AL', 'Aluminium Index'),
        ('FE', 'Iron/Steel Index'),
        ('IM', 'Import Machine Index'),
        ('W',  'Labour/Wage Index'),
        ('D',  'Import Duty %'),
        ('ER', f'Exchange Rate ({currency})'),
    ]
    for col, label in params:
        index_details.append({
            'scenario':    scenario_label,
            'vendor':      vendor.vendor_name,
            'parameter':   col,
            'label':       label,
            'basevalue':   safe_round(base_idx.get(col)),
            'basemonth':   str(base_month.date()) if hasattr(base_month, 'date') else str(base_month),
            'currentvalue':safe_round(curr_idx.get(col)),
            'currentmonth':str(curr_month.date()) if hasattr(curr_month, 'date') else str(curr_month),
        })

    return summary, index_details, total_pvc


def calculate_igbt_propulsion(item, data, tender_id, idx_df, weights):
    """
    Full IGBT Propulsion System PVC calculation.
    Scenarios:
      A2 : basicrate  + base=pvcbasedate   + current=caldate
      B2 : basicrate  + base=pvcbasedate   + current=scheduled_dp
      C1 : lowerrate  + base=lowerbasedate + current=caldate       (if lower rate given)
      D1 : lowerrate  + base=lowerbasedate + current=scheduled_dp  (if lower rate given)
    For each scenario, compute P1+P2 per vendor, take the MINIMUM across vendors
    as the payable PVC for that scenario (most-favourable-vendor rule).
    Then apply LD and select final scenario per rateapplied logic.
    """
    tender  = TenderMaster.query.get_or_404(int(tender_id))
    vendors = (TenderVendor.query
               .filter_by(tender_id=tender.id)
               .order_by(TenderVendor.id.asc())
               .all())
    if not vendors:
        raise ValueError('No vendor rows configured for the selected tender.')

    # ── merge form data with tender master defaults ──────────
    basicrate   = safe_float(data.get('basicrate')   or tender.basicrate)
    pvcbasedate = data.get('pvcbasedate')             or tender.pvcbasedate
    lowerrate   = safe_float(data.get('lowerrate')   or tender.lowerrate or 0)
    lowerbase   = data.get('lowerbasicdate')          or tender.lowerratebasedate
    freightpu   = safe_float(data.get('freightrateperunit') or tender.freightrateperunit or 0)
    lowerfreight= safe_float(data.get('lowerfreight')       or tender.lowerfreight or 0)
    quantity    = safe_float(data.get('quantity') or 1)

    # ── operational dates (always from user form) ─────────────
    cal_date    = data.get('caldate')
    orig_dp     = data.get('origdp')
    refixed_dp  = data.get('refixeddp')
    extended_dp = data.get('extendeddp')
    supply_date = data.get('supdate')
    rate_applied= (data.get('rateapplied') or '').strip().lower()

    # scheduled DP: extended > refixed > original
    scheduled_dp = extended_dp or refixed_dp or orig_dp

    # convert to timestamps
    cal_ts      = pd.to_datetime(cal_date,    errors='coerce')
    sched_ts    = pd.to_datetime(scheduled_dp,errors='coerce')
    supply_ts   = pd.to_datetime(supply_date, errors='coerce')

    base_month  = to_month_start(pvcbasedate)
    lower_base_month = to_month_start(lowerbase) if lowerbase else None

    cal_month   = to_month_start(cal_date)
    sched_month = to_month_start(scheduled_dp)

    lower_rate_applicable = lowerrate > 0 and lower_base_month is not None

    # ── freight totals ───────────────────────────────────────
    freight_total       = freightpu    * quantity
    lower_freight_total = lowerfreight * quantity

    # ── LD calculation ───────────────────────────────────────
    delay_days   = 0
    ld_weeks     = 0
    ld_rate_pct  = 0.0
    ld_applicable= False

    due_ts = sched_ts
    if pd.notna(due_ts) and pd.notna(supply_ts) and supply_ts > due_ts:
        delay_days  = int((supply_ts - due_ts).days)
        ld_weeks    = math.ceil(delay_days / 7)
        ld_rate_pct = min(ld_weeks * 0.5, 10.0)
        ld_applicable = True

    # ── compute PVC per scenario per vendor ──────────────────
    all_vendor_summaries = []
    all_index_details    = []

    def run_scenario(label, rate, base_m, ref_m):
        
        if not base_m or pd.isna(base_m):
            return 0.0
        if not ref_m or pd.isna(ref_m):
            return 0.0
        sc_summaries = []
        sc_indices   = []
        for v in vendors:
            try:
                s, idx_rows, _ = _igbt_vendor_scenario(
                    rate, v, base_m, ref_m, idx_df, weights, label
                )
                sc_summaries.append(s)
                sc_indices.extend(idx_rows)
            except ValueError as e:
                app.logger.warning(f'Vendor {v.vendor_name} scenario {label}: {e}')
        all_vendor_summaries.extend(sc_summaries)
        all_index_details.extend(sc_indices)
        if not sc_summaries:
            return 0.0
        return min(s['total_pvc'] for s in sc_summaries)

    pvc_a2 = run_scenario('A2', basicrate, base_month, cal_month)
    pvc_b2 = run_scenario('B2', basicrate, base_month, sched_month)
    pvc_c1 = None
    pvc_d1 = None
    if lower_rate_applicable:
       pvc_c1 = run_scenario('C1', lowerrate, lower_base_month, cal_month)   if lower_rate_applicable else None
       pvc_d1 = run_scenario('D1', lowerrate, lower_base_month, sched_month) if lower_rate_applicable else None

    # ── freight + GST on top ─────────────────────────────────
    def with_freight_gst(base_r, pvc_amt, qty, frt):
        return (base_r * qty + pvc_amt + frt) * GST_FACTOR

    pvc_actual       = with_freight_gst(basicrate, pvc_a2, quantity, freight_total)
    pvc_contractual  = with_freight_gst(basicrate, pvc_b2, quantity, freight_total)
    lower_actual     = with_freight_gst(lowerrate, pvc_c1 or 0, quantity, lower_freight_total) if lower_rate_applicable else None
    lower_contractual= with_freight_gst(lowerrate, pvc_d1 or 0, quantity, lower_freight_total) if lower_rate_applicable else None

    # ── LD amounts ───────────────────────────────────────────
    ldamt_actual      = max(pvc_actual, 0)      * ld_rate_pct / 100.0 if ld_applicable else 0.0
    ldamt_contractual = max(pvc_contractual, 0) * ld_rate_pct / 100.0 if ld_applicable else 0.0

    pvc_actual_less_ld      = pvc_actual      - ldamt_actual
    pvc_contractual_less_ld = pvc_contractual - ldamt_contractual
    lower_actual_less_ld    = lower_actual    - ldamt_actual      if lower_actual    is not None else None
    lower_contractual_less_ld = lower_contractual - ldamt_contractual if lower_contractual is not None else None

    # ── scenario selection ───────────────────────────────────
    if rate_applied == 'supply before due date':
        candidates = {'A2': pvc_actual}
    elif rate_applied == 'supply after due date':
        candidates = {'A2': pvc_actual_less_ld, 'B2': pvc_contractual_less_ld}
    elif rate_applied == 'lower rate applicable':
        candidates = {
            'A2': pvc_actual,
            'B2': pvc_contractual,
            'C1': lower_actual,
            'D1': lower_contractual,
        }
    elif rate_applied == 'lower rate and ld comparison':
        candidates = {
            'A2': pvc_actual_less_ld,
            'B2': pvc_contractual_less_ld,
            'C1': lower_actual,
            'D1': lower_contractual,
        }
    elif rate_applied == 'lower rate with ld in further extension':
        candidates = {
            'A2': pvc_actual_less_ld,
            'B2': pvc_contractual_less_ld,
            'C1': lower_actual_less_ld,
            'D1': lower_contractual_less_ld,
        }
    else:
        candidates = {
            'A2': pvc_actual,
            'B2': pvc_contractual,
        }
        if lower_rate_applicable:
            candidates['C1'] = lower_actual
            candidates['D1'] = lower_contractual

    candidates = {k: v for k, v in candidates.items() if v is not None}
    selected   = min(candidates, key=candidates.get) if candidates else 'A2'
    fair_price = candidates.get(selected, pvc_actual)

    # ── scenario amounts for display ─────────────────────────
    scenario_amounts = {
        'A2': safe_round(pvc_actual_less_ld),
        'B2': safe_round(pvc_contractual_less_ld),
    }
    if lower_rate_applicable:
        scenario_amounts['C1'] = safe_round(lower_actual)
        scenario_amounts['D1'] = safe_round(lower_contractual)

    # ── build IEEMA-style scenariodetails for index table ────
    # For IGBT we reuse pvc_percent_detailed using same idx_df + weights
    # so the index breakdown table in result.html also works
    scenario_details = []
    ieema_scenarios = [
        ('A2', pvcbasedate, cal_date),
        ('B2', pvcbasedate, scheduled_dp),
    ]
    if lower_rate_applicable:
        ieema_scenarios.append(('C1', lowerbase, cal_date))
        ieema_scenarios.append(('D1', lowerbase, scheduled_dp))

    for sc, bd, cd in ieema_scenarios:
        if bd and cd:
            det = pvc_percent_detailed(bd, cd, idx_df, sc, weights)
            if det:
                scenario_details.append(det)

    return {
        'pvcactual':               safe_round(pvc_actual),
        'pvccontractual':          safe_round(pvc_contractual),
        'loweractual':             safe_round(lower_actual)              if lower_rate_applicable else None,
        'lowercontractual':        safe_round(lower_contractual)         if lower_rate_applicable else None,
        'delaydays':               delay_days,
        'ldweeksnew':              ld_weeks,
        'ldratepctnew':            safe_round(ld_rate_pct),
        'ldapplicable':            ld_applicable,
        'ldamtactual':             safe_round(ldamt_actual),
        'ldamtcontractual':        safe_round(ldamt_contractual),
        'pvcactuallessldnew':      safe_round(pvc_actual_less_ld),
        'pvccontractuallessldnew': safe_round(pvc_contractual_less_ld),
        'loweractuallessld':       safe_round(lower_actual_less_ld)      if lower_actual_less_ld    is not None else None,
        'lowercontractuallessld':  safe_round(lower_contractual_less_ld) if lower_contractual_less_ld is not None else None,
        'fairpricenew':            safe_round(fair_price),
        'selectedscenarionew':     selected,
        'pvcperseta2':             safe_round(pvc_a2),
        'pvcpersetb2':             safe_round(pvc_b2),
        'pvcpersetc1':             safe_round(pvc_c1) if pvc_c1 is not None else None,
        'pvcpersetd1':             safe_round(pvc_d1) if pvc_d1 is not None else None,
        'scenarioamounts':         scenario_amounts,
        'scenariodetails':         scenario_details,
        'igbt_vendor_details':     all_vendor_summaries,
        'igbt_index_details':      all_index_details,
        'tenderno':                tender.tender_no,
        'pono':                    vendors[0].po_no if vendors else None,
    }


# ─────────────────────────────────────────────────────────────
# IEEMA SINGLE RECORD CALC
# ─────────────────────────────────────────────────────────────
def calc_single_record(data, idx_df, weights):
    pvc_base_date  = data.get('pvcbasedate')
    cal_date       = data.get('caldate')
    orig_dp        = data.get('origdp')
    refixed_dp     = data.get('refixeddp')
    extended_dp    = data.get('extendeddp')
    scheduled_date = extended_dp or refixed_dp or orig_dp
    supply_date    = data.get('supdate')
    lower_basic_date = data.get('lowerbasicdate')

    qty              = safe_float(data.get('quantity'))
    basic_rate       = safe_float(data.get('basicrate'))
    freight_rate_pu  = safe_float(data.get('freightrateperunit'))
    lower_rate       = safe_float(data.get('lowerrate'))
    lower_freight    = safe_float(data.get('lowerfreight'))

    freight_total        = freight_rate_pu * qty
    lower_freight_total  = lower_freight   * qty

    pct_a2 = pvc_percent(pvc_base_date,   cal_date,       idx_df, weights)
    pct_b2 = pvc_percent(pvc_base_date,   scheduled_date, idx_df, weights)
    pct_c1 = pvc_percent(lower_basic_date, cal_date,       idx_df, weights) if lower_basic_date else None
    pct_d1 = pvc_percent(lower_basic_date, scheduled_date, idx_df, weights) if lower_basic_date else None

    base_amt         = basic_rate * qty
    lower_amt        = lower_rate * qty

    pvc_actual       = (base_amt  * (1 + (pct_a2 / 100.0)) + freight_total)       * GST_FACTOR
    pvc_contractual  = (base_amt  * (1 + (pct_b2 / 100.0)) + freight_total)       * GST_FACTOR
    lower_actual     = (lower_amt * (1 + ((pct_c1 or 0) / 100.0)) + lower_freight_total) * GST_FACTOR if lower_rate else None
    lower_contractual= (lower_amt * (1 + ((pct_d1 or 0) / 100.0)) + lower_freight_total) * GST_FACTOR if lower_rate else None

    # ── LD ───────────────────────────────────────────────────
    delay_days   = 0
    ld_weeks     = 0
    ld_rate_pct  = 0.0
    ld_applicable= False
    ldamt_actual = ldamt_contractual = 0.0

    due_ts    = pd.to_datetime(scheduled_date, errors='coerce')
    supply_ts = pd.to_datetime(supply_date,    errors='coerce')

    if pd.notna(due_ts) and pd.notna(supply_ts) and supply_ts > due_ts:
        delay_days    = int((supply_ts - due_ts).days)
        ld_weeks      = math.ceil(delay_days / 7)
        ld_rate_pct   = min(ld_weeks * 0.5, 10.0)
        ld_applicable = True
        ldamt_actual      = max(pvc_actual, 0)      * ld_rate_pct / 100.0
        ldamt_contractual = max(pvc_contractual, 0) * ld_rate_pct / 100.0

    pvc_actual_less_ld        = pvc_actual      - ldamt_actual
    pvc_contractual_less_ld   = pvc_contractual - ldamt_contractual
    lower_actual_less_ld      = lower_actual    - ldamt_actual      if lower_actual    is not None else None
    lower_contractual_less_ld = lower_contractual - ldamt_contractual if lower_contractual is not None else None

    # ── scenario selection ───────────────────────────────────
    rate_applied = (data.get('rateapplied') or '').strip().lower()

    if rate_applied == 'supply before due date':
        candidates = {'A2': pvc_actual}
    elif rate_applied == 'supply after due date':
        candidates = {'A2': pvc_actual_less_ld, 'B2': pvc_contractual_less_ld}
    elif rate_applied == 'lower rate applicable':
        candidates = {
            'A2': pvc_actual,
            'B2': pvc_contractual,
            'C1': lower_actual,
            'D1': lower_contractual,
        }
    elif rate_applied == 'lower rate and ld comparison':
        candidates = {
            'A2': pvc_actual_less_ld,
            'B2': pvc_contractual_less_ld,
            'C1': lower_actual,
            'D1': lower_contractual,
        }
    elif rate_applied == 'lower rate with ld in further extension':
        candidates = {
            'A2': pvc_actual_less_ld,
            'B2': pvc_contractual_less_ld,
            'C1': lower_actual_less_ld,
            'D1': lower_contractual_less_ld,
        }
    else:
        candidates = {'A2': pvc_actual, 'B2': pvc_contractual}
        if lower_rate:
            candidates['C1'] = lower_actual
            candidates['D1'] = lower_contractual

    candidates = {k: v for k, v in candidates.items() if v is not None}
    selected   = min(candidates, key=candidates.get) if candidates else 'A2'
    fair_price = candidates.get(selected, pvc_actual)

    scenario_amounts = {
        'A2': safe_round(pvc_actual_less_ld),
        'B2': safe_round(pvc_contractual_less_ld),
    }
    if lower_rate:
        scenario_amounts['C1'] = safe_round(lower_actual)
        scenario_amounts['D1'] = safe_round(lower_contractual)

    # ── index-wise scenario detail ───────────────────────────
    scenario_details = []
    for sc, bd, cd in [
        ('A2', pvc_base_date,    cal_date),
        ('B2', pvc_base_date,    scheduled_date),
        ('C1', lower_basic_date, cal_date),
        ('D1', lower_basic_date, scheduled_date),
    ]:
        if bd and cd:
            det = pvc_percent_detailed(bd, cd, idx_df, sc, weights)
            if det:
                scenario_details.append(det)

    return {
        'pvcactual':               safe_round(pvc_actual),
        'pvccontractual':          safe_round(pvc_contractual),
        'loweractual':             safe_round(lower_actual)              if lower_actual    is not None else None,
        'lowercontractual':        safe_round(lower_contractual)         if lower_contractual is not None else None,
        'delaydays':               delay_days,
        'ldweeksnew':              ld_weeks,
        'ldratepctnew':            safe_round(ld_rate_pct),
        'ldapplicable':            ld_applicable,
        'ldamtactual':             safe_round(ldamt_actual),
        'ldamtcontractual':        safe_round(ldamt_contractual),
        'pvcactuallessldnew':      safe_round(pvc_actual_less_ld),
        'pvccontractuallessldnew': safe_round(pvc_contractual_less_ld),
        'loweractuallessld':       safe_round(lower_actual_less_ld)      if lower_actual_less_ld    is not None else None,
        'lowercontractuallessld':  safe_round(lower_contractual_less_ld) if lower_contractual_less_ld is not None else None,
        'fairpricenew':            safe_round(fair_price),
        'selectedscenarionew':     selected,
        'pvcperseta2':             safe_round(base_amt * pct_a2 / 100.0),
        'pvcpersetb2':             safe_round(base_amt * pct_b2 / 100.0),
        'pvcpersetc1':             safe_round(lower_amt * (pct_c1 or 0) / 100.0) if lower_rate else None,
        'pvcpersetd1':             safe_round(lower_amt * (pct_d1 or 0) / 100.0) if lower_rate else None,
        'scenarioamounts':         scenario_amounts,
        'scenariodetails':         scenario_details,
        'igbt_vendor_details':     [],
        'igbt_index_details':      [],
        'tenderno':                None,
        'pono':                    None,
    }


# ─────────────────────────────────────────────────────────────
# ROUTER – picks IGBT or IEEMA
# ─────────────────────────────────────────────────────────────
def calculate_for_item(item, data, idx_df, weights):
    code = (item.pvc_formula_code or '').replace('_', '').upper()
    if code == 'IGBTPROPULSIONSYSTEM':
        tender_id = data.get('tenderid')
        if not tender_id:
            raise ValueError('Tender is required for IGBT Propulsion System.')
        return calculate_igbt_propulsion(item, data, tender_id, idx_df, weights)
    return calc_single_record(data, idx_df, weights)


# ─────────────────────────────────────────────────────────────
# RESULT OBJECT (passed to templates)
# ─────────────────────────────────────────────────────────────
class ResultObj:
    def __init__(self, payload):
        self.data                = payload
        self.scenarioamounts     = payload.get('scenarioamounts', {})
        self.scenariodetails     = payload.get('scenariodetails', [])
        self.igbt_vendor_details = payload.get('igbt_vendor_details', [])
        self.igbt_index_details  = payload.get('igbt_index_details', [])


# ─────────────────────────────────────────────────────────────
# AUTH ROUTES
# ─────────────────────────────────────────────────────────────
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username    = (request.form.get('username')    or '').strip()
        password    = (request.form.get('password')    or '')
        full_name   = (request.form.get('fullname')    or '').strip()
        email       = (request.form.get('email')       or '').strip()
        contact_no  = (request.form.get('contactno')   or '').strip()
        designation = (request.form.get('designation') or '').strip()
        control_no  = (request.form.get('controlno')   or '').strip()

        if not username or not password:
            flash('Username and password are required.', 'danger')
            return redirect(url_for('register'))
        if User.query.filter_by(username=username).first():
            flash('Username already exists.', 'danger')
            return redirect(url_for('register'))
        if email and User.query.filter_by(email=email).first():
            flash('Email already registered.', 'danger')
            return redirect(url_for('register'))

        user = User(
            username      = username,
            password_hash = generate_password_hash(password),
            full_name     = full_name,
            email         = email or None,
            contact_no    = contact_no,
            designation   = designation,
            control_no    = control_no,
            is_admin      = False,
        )
        db.session.add(user)
        db.session.commit()
        flash('Registration successful. Please login.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = (request.form.get('username') or '').strip()
        password =  request.form.get('password') or ''
        user     = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            return redirect(url_for('index'))
        flash('Invalid username or password.', 'danger')
    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))


# ─────────────────────────────────────────────────────────────
# MAIN CALCULATOR
# ─────────────────────────────────────────────────────────────
@app.route('/')
@login_required
def index():
    items   = Item.query.order_by(Item.name.asc()).all()
    tenders = TenderMaster.query.order_by(TenderMaster.tender_no.asc()).all()
    return render_template('index.html', items=items, tenders=tenders)


@app.route('/calculate', methods=['POST'])
@login_required
def calculate():
    item_id = request.form.get('itemid') or request.form.get('item_id')
    if not item_id:
        flash('Please select an item.', 'danger')
        return redirect(url_for('index'))

    item   = Item.query.get_or_404(int(item_id))
    idx_df = get_item_index_df(item)
    if idx_df.empty:
        flash('Indices not configured for this item. Please add in Admin → Item Indices.', 'danger')
        return redirect(url_for('index'))

    try:
        weights = json.loads(item.weights_json or '{}')
    except Exception:
        weights = {}

    pvc_input          = PVCInput(request.form)
    pvc_input.user_id  = current_user.id
    pvc_input.username = current_user.username
    data               = pvc_input.to_dict()

    try:
        result_row = calculate_for_item(item, data, idx_df, weights)
    except ValueError as e:
        flash(str(e), 'danger')
        return redirect(url_for('index'))
    except Exception:
        app.logger.exception('PVC calculation failed')
        flash('Calculation failed. Please check your inputs and index data.', 'danger')
        return redirect(url_for('index'))

    # ── build flat payload for template + DB ─────────────────
    payload = {
        'pvcactual':               result_row.get('pvcactual',               0.0),
        'pvccontractual':          result_row.get('pvccontractual',           0.0),
        'loweractual':             result_row.get('loweractual',              0.0),
        'lowercontractual':        result_row.get('lowercontractual',         0.0),
        'ldamtactual':             result_row.get('ldamtactual',              0.0),
        'ldamtcontractual':        result_row.get('ldamtcontractual',         0.0),
        'fairprice':               result_row.get('fairpricenew',             0.0),
        'pvcactuallessldnew':      result_row.get('pvcactuallessldnew'),
        'pvccontractuallessldnew': result_row.get('pvccontractuallessldnew'),
        'loweractuallessld':       result_row.get('loweractuallessld'),
        'lowercontractuallessld':  result_row.get('lowercontractuallessld'),
        'delaydays':               result_row.get('delaydays',                0),
        'ldweeks':                 result_row.get('ldweeksnew',               0),
        'ldratepct':               result_row.get('ldratepctnew',             0.0),
        'ldapplicable':            result_row.get('ldapplicable',             False),
        'selectedscenario':        result_row.get('selectedscenarionew'),
        'pvcperseta2':             result_row.get('pvcperseta2'),
        'pvcpersetb2':             result_row.get('pvcpersetb2'),
        'pvcpersetc1':             result_row.get('pvcpersetc1'),
        'pvcpersetd1':             result_row.get('pvcpersetd1'),
        'tenderno':                result_row.get('tenderno'),
        'pono':                    result_row.get('pono'),
        'scenarioamounts':         result_row.get('scenarioamounts',          {}),
        'scenariodetails':         result_row.get('scenariodetails',          []),
        'igbt_vendor_details':     result_row.get('igbt_vendor_details',      []),
        'igbt_index_details':      result_row.get('igbt_index_details',       []),
    }

    # ── save to DB ────────────────────────────────────────────
    calc = PVCResult(
        user_id                  = pvc_input.user_id,
        username                 = pvc_input.username,
        item_id                  = item.id,
        basicrate                = data.get('basicrate',          0),
        quantity                 = data.get('quantity',           0),
        freightrateperunit       = data.get('freightrateperunit', 0),
        pvcbasedate              = data.get('pvcbasedate'),
        origdp                   = data.get('origdp'),
        refixeddp                = data.get('refixeddp'),
        extendeddp               = data.get('extendeddp'),
        caldate                  = data.get('caldate'),
        supdate                  = data.get('supdate'),
        rateapplied              = data.get('rateapplied'),
        pvcactual                = payload['pvcactual'],
        pvccontractual           = payload['pvccontractual'],
        loweractual              = payload['loweractual'],
        lowercontractual         = payload['lowercontractual'],
        ldamtactual              = payload['ldamtactual'],
        ldamtcontractual         = payload['ldamtcontractual'],
        fairprice                = payload['fairprice'],
        selectedscenario         = payload['selectedscenario'],
        pvcactuallessldnew       = payload['pvcactuallessldnew'],
        pvccontractuallessldnew  = payload['pvccontractuallessldnew'],
        loweractuallessld        = payload['loweractuallessld'],
        lowercontractuallessld   = payload['lowercontractuallessld'],
        delaydays                = payload['delaydays'],
        ldweeksnew               = payload['ldweeks'],
        ldratepctnew             = payload['ldratepct'],
        ldapplicable             = payload['ldapplicable'],
        pvcperseta2              = payload['pvcperseta2'],
        pvcpersetb2              = payload['pvcpersetb2'],
        pvcpersetc1              = payload['pvcpersetc1'],
        pvcpersetd1              = payload['pvcpersetd1'],
        tenderno                 = payload['tenderno'],
        pono                     = payload['pono'],
        scenarioamounts_json     = json.dumps(payload['scenarioamounts']),
        scenariodetails_json     = json.dumps(payload['scenariodetails']),
        igbt_vendor_details_json = json.dumps(payload['igbt_vendor_details']),
    )
    db.session.add(calc)
    db.session.commit()

    return render_template(
        'result.html',
        item     = item.name,
        item_obj = item,
        data     = data,
        result   = ResultObj(payload),
        calc_id  = calc.id,
    )


# ─────────────────────────────────────────────────────────────
# HISTORY
# ─────────────────────────────────────────────────────────────
@app.route('/history')
@login_required
def history():
    records = (PVCResult.query
               .filter_by(user_id=current_user.id)
               .order_by(PVCResult.created_at.desc())
               .all())
    return render_template('history.html', records=records)


# ─────────────────────────────────────────────────────────────
# VIEW SAVED CALC
# ─────────────────────────────────────────────────────────────
@app.route('/calc/<int:calcid>')
@login_required
def viewcalc(calcid):
    calc = PVCResult.query.filter_by(
        id=calcid, user_id=current_user.id
    ).first_or_404()
    item = calc.item

    data = {
        'basicrate':          calc.basicrate,
        'quantity':           calc.quantity,
        'freightrateperunit': calc.freightrateperunit,
        'pvcbasedate':        calc.pvcbasedate,
        'origdp':             calc.origdp,
        'refixeddp':          calc.refixeddp,
        'extendeddp':         calc.extendeddp,
        'caldate':            calc.caldate,
        'supdate':            calc.supdate,
        'rateapplied':        calc.rateapplied,
        'lowerrate':          calc.loweractual,
        'lowerfreight':       0,
        'lowerbasicdate':     None,
    }

    payload = {
        'pvcactual':               calc.pvcactual,
        'pvccontractual':          calc.pvccontractual,
        'loweractual':             calc.loweractual,
        'lowercontractual':        calc.lowercontractual,
        'ldamtactual':             calc.ldamtactual,
        'ldamtcontractual':        calc.ldamtcontractual,
        'fairprice':               calc.fairprice,
        'selectedscenario':        calc.selectedscenario,
        'ldapplicable':            calc.ldapplicable,
        'pvcactuallessldnew':      calc.pvcactuallessldnew,
        'pvccontractuallessldnew': calc.pvccontractuallessldnew,
        'loweractuallessld':       calc.loweractuallessld,
        'lowercontractuallessld':  calc.lowercontractuallessld,
        'delaydays':               calc.delaydays,
        'ldweeks':                 calc.ldweeksnew,
        'ldratepct':               calc.ldratepctnew,
        'pvcperseta2':             calc.pvcperseta2,
        'pvcpersetb2':             calc.pvcpersetb2,
        'pvcpersetc1':             calc.pvcpersetc1,
        'pvcpersetd1':             calc.pvcpersetd1,
        'tenderno':                calc.tenderno,
        'pono':                    calc.pono,
        'scenarioamounts':         json.loads(calc.scenarioamounts_json     or '{}'),
        'scenariodetails':         json.loads(calc.scenariodetails_json     or '[]'),
        'igbt_vendor_details':     json.loads(calc.igbt_vendor_details_json or '[]'),
        'igbt_index_details':      [],
    }

    return render_template(
        'result.html',
        item     = item.name if item else '',
        item_obj = item,
        data     = data,
        result   = ResultObj(payload),
        calc_id  = calc.id,
    )


# ─────────────────────────────────────────────────────────────
# EXCEL EXPORT
# ─────────────────────────────────────────────────────────────
@app.route('/calc/<int:calcid>/excel')
@login_required
def exportcalcexcel(calcid):
    calc = PVCResult.query.filter_by(
        id=calcid, user_id=current_user.id
    ).first_or_404()
    item = calc.item

    # ── main result sheet ─────────────────────────────────────
    main_data = [{
        'Calc ID':            calc.id,
        'User':               calc.username,
        'Item':               item.name if item else '',
        'Basic Rate':         calc.basicrate,
        'Quantity':           calc.quantity,
        'Freight/Unit':       calc.freightrateperunit,
        'PVC Base Date':      calc.pvcbasedate,
        'Original DP':        calc.origdp,
        'Refixed DP':         calc.refixeddp,
        'Extended DP':        calc.extendeddp,
        'Call Date':          calc.caldate,
        'Supply Date':        calc.supdate,
        'Rate Applied':       calc.rateapplied,
        'PVC Actual':         calc.pvcactual,
        'PVC Contractual':    calc.pvccontractual,
        'Lower Actual':       calc.loweractual,
        'Lower Contractual':  calc.lowercontractual,
        'LD Days':            calc.delaydays,
        'LD Weeks':           calc.ldweeksnew,
        'LD Rate %':          calc.ldratepctnew,
        'LD Amt Actual':      calc.ldamtactual,
        'LD Amt Contractual': calc.ldamtcontractual,
        'PVC Actual-LD':      calc.pvcactuallessldnew,
        'PVC Contractual-LD': calc.pvccontractuallessldnew,
        'Lower Actual-LD':    calc.loweractuallessld,
        'Lower Contr-LD':     calc.lowercontractuallessld,
        'Fair Price':         calc.fairprice,
        'Selected Scenario':  calc.selectedscenario,
        'Tender No':          calc.tenderno,
        'PO No':              calc.pono,
    }]

    # ── scenario amounts sheet ────────────────────────────────
    scenario_amounts = json.loads(calc.scenarioamounts_json or '{}')
    sa_data = [{'Scenario': k, 'Amount': v} for k, v in scenario_amounts.items()]

    # ── index-wise detail sheet ───────────────────────────────
    scenario_details = json.loads(calc.scenariodetails_json or '[]')
    sd_data = []
    for det in scenario_details:
        row = {
            'Scenario':     det.get('scenario'),
            'Base Month':   det.get('basemonth'),
            'Current Month':det.get('currentmonth'),
            'PVC %':        det.get('pvcpercent'),
        }
        # add each index key dynamically
        for k, v in det.items():
            if k not in ('scenario', 'basemonth', 'currentmonth', 'pvcpercent'):
                row[k] = v
        sd_data.append(row)

    # ── IGBT vendor detail sheet ──────────────────────────────
    igbt_vendors = json.loads(calc.igbt_vendor_details_json or '[]')

    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        pd.DataFrame(main_data).to_excel(
            writer, index=False, sheet_name='PVC Result'
        )
        if sa_data:
            pd.DataFrame(sa_data).to_excel(
                writer, index=False, sheet_name='Scenario Amounts'
            )
        if sd_data:
            pd.DataFrame(sd_data).to_excel(
                writer, index=False, sheet_name='Index Details'
            )
        if igbt_vendors:
            pd.DataFrame(igbt_vendors).to_excel(
                writer, index=False, sheet_name='IGBT Vendors'
            )
    output.seek(0)

    return send_file(
        output,
        as_attachment=True,
        download_name=f'PVC_Calc_{calc.id}.xlsx',
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    )


# ─────────────────────────────────────────────────────────────
# TENDER API (used by index.html JS autofill)
# ─────────────────────────────────────────────────────────────
@app.route('/get_tender/<int:tenderid>')
@login_required
def gettender(tenderid):
    tender = TenderMaster.query.get_or_404(tenderid)
    return jsonify({
        'basicrate':          tender.basicrate,
        'freightrateperunit': tender.freightrateperunit,
        'pvcbasedate':        tender.pvcbasedate,
        'lowerrate':          tender.lowerrate,
        'lowerfreight':       tender.lowerfreight,
        'lowerbasicdate':     tender.lowerratebasedate,
        'itemid':             tender.item_id,
        'tenderno':           tender.tender_no,
    })


# ─────────────────────────────────────────────────────────────
# ADMIN – TENDERS
# ─────────────────────────────────────────────────────────────
@app.route('/admin/tenders')
@login_required
@admin_required
def admintenderslist():
    tenders = TenderMaster.query.order_by(TenderMaster.created_at.desc()).all()
    return render_template('admin_tenders_list.html', tenders=tenders)


@app.route('/admin/tenders/new', methods=['GET', 'POST'])
@login_required
@admin_required
def admintendersnew():
    items = Item.query.order_by(Item.name.asc()).all()
    if request.method == 'POST':
        itemid   = request.form.get('itemid')
        tenderno = (request.form.get('tenderno') or '').strip()
        if not itemid or not tenderno:
            flash('Item and Tender No are required.', 'danger')
            return redirect(url_for('admintendersnew'))
        if TenderMaster.query.filter_by(tender_no=tenderno).first():
            flash('Tender No already exists.', 'danger')
            return redirect(url_for('admintendersnew'))
        row = TenderMaster(
            item_id           = int(itemid),
            tender_no         = tenderno,
            basicrate         = safe_float(request.form.get('basicrate')),
            pvcbasedate       = request.form.get('pvcbasedate') or '',
            lowerrate         = safe_float(request.form.get('lowerrate')),
            lowerratebasedate = request.form.get('lowerratebasedate') or '',
            freightrateperunit= safe_float(request.form.get('freightrateperunit')),
            lowerfreight      = safe_float(request.form.get('lowerfreight')),
        )
        db.session.add(row)
        db.session.commit()
        flash('Tender added successfully.', 'success')
        return redirect(url_for('admintenderslist'))
    return render_template('admin_tenders_form.html', tender=None, items=items)


@app.route('/admin/tenders/<int:tenderid>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def admintendersedit(tenderid):
    tender = TenderMaster.query.get_or_404(tenderid)
    items  = Item.query.order_by(Item.name.asc()).all()
    if request.method == 'POST':
        itemid   = request.form.get('itemid')
        tenderno = (request.form.get('tenderno') or '').strip()
        if not itemid or not tenderno:
            flash('Item and Tender No are required.', 'danger')
            return redirect(url_for('admintendersedit', tenderid=tender.id))
        existing = TenderMaster.query.filter(
            TenderMaster.tender_no == tenderno,
            TenderMaster.id != tender.id
        ).first()
        if existing:
            flash('Tender No already exists.', 'danger')
            return redirect(url_for('admintendersedit', tenderid=tender.id))
        tender.item_id            = int(itemid)
        tender.tender_no          = tenderno
        tender.basicrate          = safe_float(request.form.get('basicrate'))
        tender.pvcbasedate        = request.form.get('pvcbasedate') or ''
        tender.lowerrate          = safe_float(request.form.get('lowerrate'))
        tender.lowerratebasedate  = request.form.get('lowerratebasedate') or ''
        tender.freightrateperunit = safe_float(request.form.get('freightrateperunit'))
        tender.lowerfreight       = safe_float(request.form.get('lowerfreight'))
        db.session.commit()
        flash('Tender updated successfully.', 'success')
        return redirect(url_for('admintenderslist'))
    return render_template('admin_tenders_form.html', tender=tender, items=items)


# ─────────────────────────────────────────────────────────────
# ADMIN – TENDER VENDORS
# ─────────────────────────────────────────────────────────────
@app.route('/admin/tenders/<int:tenderid>/vendors')
@login_required
@admin_required
def admintendervendorslist(tenderid):
    tender  = TenderMaster.query.get_or_404(tenderid)
    vendors = (TenderVendor.query
               .filter_by(tender_id=tender.id)
               .order_by(TenderVendor.id.asc())
               .all())
    return render_template(
        'admin_tender_vendors_list.html', tender=tender, vendors=vendors
    )


@app.route('/admin/tenders/<int:tenderid>/vendors/new', methods=['GET', 'POST'])
@login_required
@admin_required
def admintendervendorsnew(tenderid):
    tender = TenderMaster.query.get_or_404(tenderid)
    if request.method == 'POST':
        vendorname = (request.form.get('vendorname') or '').strip()
        currency   = (request.form.get('currency')   or '').strip().upper()
        if not vendorname or not currency:
            flash('Vendor name and currency are required.', 'danger')
            return redirect(url_for('admintendervendorsnew', tenderid=tender.id))
        row = TenderVendor(
            tender_id   = tender.id,
            po_no       = request.form.get('pono'),
            vendor_name = vendorname,
            cif         = safe_float(request.form.get('cif')),
            currency    = currency,
        )
        db.session.add(row)
        db.session.commit()
        flash('Vendor added successfully.', 'success')
        return redirect(url_for('admintendervendorslist', tenderid=tender.id))
    return render_template(
        'admin_tender_vendor_form.html', tender=tender, vendor=None
    )


@app.route('/admin/tenders/<int:tenderid>/vendors/<int:vendorid>/edit',
           methods=['GET', 'POST'])
@login_required
@admin_required
def admintendervendorsedit(tenderid, vendorid):
    tender = TenderMaster.query.get_or_404(tenderid)
    vendor = TenderVendor.query.filter_by(
        id=vendorid, tender_id=tender.id
    ).first_or_404()
    if request.method == 'POST':
        vendorname = (request.form.get('vendorname') or '').strip()
        currency   = (request.form.get('currency')   or '').strip().upper()
        if not vendorname or not currency:
            flash('Vendor name and currency are required.', 'danger')
            return redirect(url_for(
                'admintendervendorsedit', tenderid=tender.id, vendorid=vendor.id
            ))
        vendor.vendor_name = vendorname
        vendor.po_no       = request.form.get('pono')
        vendor.cif         = safe_float(request.form.get('cif'))
        vendor.currency    = currency
        db.session.commit()
        flash('Vendor updated successfully.', 'success')
        return redirect(url_for('admintendervendorslist', tenderid=tender.id))
    return render_template(
        'admin_tender_vendor_form.html', tender=tender, vendor=vendor
    )


# ─────────────────────────────────────────────────────────────
# ADMIN – ITEMS
# ─────────────────────────────────────────────────────────────
@app.route('/admin/items')
@login_required
@admin_required
def adminitemslist():
    items = Item.query.order_by(Item.name.asc()).all()
    return render_template('admin_items_list.html', items=items)


@app.route('/admin/items/new', methods=['GET', 'POST'])
@login_required
@admin_required
def adminitemsnew():
    if request.method == 'POST':
        name            = (request.form.get('name')           or '').strip()
        code            = (request.form.get('code')           or '').strip()
        formula         = (request.form.get('pvcformulacode') or '').strip()
        weightsjson     = (request.form.get('weightsjson')    or '{}').strip()
        extrafieldsjson = (request.form.get('extrafieldsjson')or '[]').strip()
        description     =  request.form.get('description')

        if not name or not formula:
            flash('Name and formula code are required.', 'danger')
            return redirect(url_for('adminitemsnew'))
        try:
            json.loads(weightsjson)
            json.loads(extrafieldsjson)
        except Exception:
            flash('Weights / Extra fields must be valid JSON.', 'danger')
            return redirect(url_for('adminitemsnew'))

        it = Item(
            name              = name,
            code              = code or None,
            pvc_formula_code  = formula,
            weights_json      = weightsjson,
            extra_fields_json = extrafieldsjson,
            description       = description,
        )
        db.session.add(it)
        db.session.commit()
        flash('Item added successfully.', 'success')
        return redirect(url_for('adminitemslist'))
    return render_template('admin_items_form.html', item=None)


@app.route('/admin/items/<int:itemid>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def adminitemsedit(itemid):
    it = Item.query.get_or_404(itemid)
    if request.method == 'POST':
        name            = (request.form.get('name')           or '').strip()
        code            = (request.form.get('code')           or '').strip()
        formula         = (request.form.get('pvcformulacode') or '').strip()
        weightsjson     = (request.form.get('weightsjson')    or '{}').strip()
        extrafieldsjson = (request.form.get('extrafieldsjson')or '[]').strip()
        description     =  request.form.get('description')

        if not name or not formula:
            flash('Name and formula code are required.', 'danger')
            return redirect(url_for('adminitemsedit', itemid=it.id))
        try:
            json.loads(weightsjson)
            json.loads(extrafieldsjson)
        except Exception:
            flash('Weights / Extra fields must be valid JSON.', 'danger')
            return redirect(url_for('adminitemsedit', itemid=it.id))

        it.name              = name
        it.code              = code or None
        it.pvc_formula_code  = formula
        it.weights_json      = weightsjson
        it.extra_fields_json = extrafieldsjson
        it.description       = description
        db.session.commit()
        flash('Item updated successfully.', 'success')
        return redirect(url_for('adminitemslist'))
    return render_template('admin_items_form.html', item=it)


# ─────────────────────────────────────────────────────────────
# ADMIN – ITEM INDICES
# ─────────────────────────────────────────────────────────────
@app.route('/admin/items/<int:itemid>/indices')
@login_required
@admin_required
def adminitemindiceslist(itemid):
    item = Item.query.get_or_404(itemid)
    rows = (ItemIndex.query
            .filter_by(item_id=item.id)
            .order_by(ItemIndex.month.desc())
            .all())
    return render_template('admin_item_indices_list.html', item=item, rows=rows)


@app.route('/admin/items/<int:itemid>/indices/new', methods=['GET', 'POST'])
@login_required
@admin_required
def adminitemindicesnew(itemid):
    item = Item.query.get_or_404(itemid)
    if request.method == 'POST':
        try:
            month_str = request.form.get('month') or ''
            m = datetime.strptime(month_str, '%Y-%m-%d').date()
            m = date(m.year, m.month, 1)
        except Exception:
            flash('Invalid month date. Use YYYY-MM-DD format.', 'danger')
            return redirect(url_for('adminitemindicesnew', itemid=item.id))

        indicesjson = (request.form.get('indicesjson') or '').strip()
        try:
            json.loads(indicesjson)
        except Exception:
            flash('Indices must be valid JSON, e.g. {"C":100,"AL":200}', 'danger')
            return redirect(url_for('adminitemindicesnew', itemid=item.id))

        # check duplicate month
        existing = ItemIndex.query.filter_by(item_id=item.id, month=m).first()
        if existing:
            flash(f'Indices for {m.strftime("%B %Y")} already exist. Edit instead.', 'warning')
            return redirect(url_for('adminitemindiceslist', itemid=item.id))

        row = ItemIndex(item_id=item.id, month=m, indices_json=indicesjson)
        db.session.add(row)
        db.session.commit()
        flash(f'Indices for {m.strftime("%B %Y")} added.', 'success')
        return redirect(url_for('adminitemindiceslist', itemid=item.id))
    return render_template('admin_item_indices_form.html', item=item, row=None)


@app.route('/admin/items/<int:itemid>/indices/<int:rowid>/edit',
           methods=['GET', 'POST'])
@login_required
@admin_required
def adminitemindicesedit(itemid, rowid):
    item = Item.query.get_or_404(itemid)
    row  = ItemIndex.query.filter_by(id=rowid, item_id=item.id).first_or_404()
    if request.method == 'POST':
        try:
            month_str = request.form.get('month') or ''
            m = datetime.strptime(month_str, '%Y-%m-%d').date()
            row.month = date(m.year, m.month, 1)
        except Exception:
            flash('Invalid month date. Use YYYY-MM-DD format.', 'danger')
            return redirect(url_for(
                'adminitemindicesedit', itemid=item.id, rowid=row.id
            ))

        indicesjson = (request.form.get('indicesjson') or '').strip()
        try:
            json.loads(indicesjson)
        except Exception:
            flash('Indices must be valid JSON, e.g. {"C":100,"AL":200}', 'danger')
            return redirect(url_for(
                'adminitemindicesedit', itemid=item.id, rowid=row.id
            ))

        row.indices_json = indicesjson
        db.session.commit()
        flash(f'Indices for {row.month.strftime("%B %Y")} updated.', 'success')
        return redirect(url_for('adminitemindiceslist', itemid=item.id))
    return render_template('admin_item_indices_form.html', item=item, row=row)


# ─────────────────────────────────────────────────────────────
# DB INIT + SEED
# ─────────────────────────────────────────────────────────────
def init_db():
    db.create_all()

    # default admin user
    if not User.query.filter_by(username='admin').first():
        admin = User(
            username      = 'admin',
            password_hash = generate_password_hash('admin123'),
            full_name     = 'Administrator',
            is_admin      = True,
        )
        db.session.add(admin)
        db.session.commit()
        print('✔  Admin user created  →  admin / admin123')

    # seed one default IEEMA transformer item if table is empty
    if Item.query.count() == 0:
        default_weights = {
            'copper':   40,
            'crgo':     24,
            'ms':        8,
            'insmat':    4,
            'transoil':  8,
            'wpi':       8,
        }
        itm = Item(
            name             = 'Main Transformer 6531 KVA (PL NO: 29721008)',
            code             = 'TRANSFORMER_6531',
            pvc_formula_code = 'POWERTRFIEEMA',
            weights_json     = json.dumps(default_weights),
            extra_fields_json= '[]',
            description      = 'Default transformer – IEEMA PVC formula.',
        )
        db.session.add(itm)
        db.session.commit()
        print('✔  Seeded default item: Main Transformer 6531 KVA')

    # seed one default IGBT item if no IGBT item exists
    igbt_exists = Item.query.filter(
        Item.pvc_formula_code.ilike('%IGBT%')
    ).first()
    if not igbt_exists:
        igbt_weights = {
            'FIXED': 16,
            'C':     26,
            'AL':    13,
            'FE':    18,
            'IM':     9,
            'W':     18,
        }
        igbt_item = Item(
            name             = 'IGBT Propulsion System',
            code             = 'IGBT_PROP',
            pvc_formula_code = 'IGBTPROPULSIONSYSTEM',
            weights_json     = json.dumps(igbt_weights),
            extra_fields_json= '[]',
            description      = 'IGBT Propulsion – P1/P2 vendor-wise PVC formula.',
        )
        db.session.add(igbt_item)
        db.session.commit()
        print('✔  Seeded default IGBT item: IGBT Propulsion System')


# ─────────────────────────────────────────────────────────────
# STARTUP
# ─────────────────────────────────────────────────────────────
with app.app_context():
    init_db()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_DEBUG', 'true').lower() == 'true'
    app.run(host='0.0.0.0', port=port, debug=debug)