"""
Shared numeric and date helpers used by pvc_ieema and pvc_igbt.
"""
import json
import math
from datetime import datetime, date
from functools import lru_cache

import pandas as pd
from dateutil.relativedelta import relativedelta


# ───────────────────────────────────────────────────────────────
def safe_float(x: object) -> float:
    """Convert anything to float; return 0.0 on failure."""
    try:
        return float(str(x or 0).replace(',', '').strip())
    except (ValueError, TypeError):
        return 0.0


def safe_round(x: object, n: int = 2):
    """Round to n decimal places; return None on failure."""
    try:
        return round(float(x), n)
    except (ValueError, TypeError):
        return None


def parse_date_ymd(value: str) -> date | None:
    """Parse YYYY-MM-DD string to date; return None on failure."""
    if not value:
        return None
    try:
        return datetime.strptime(value.strip(), '%Y-%m-%d').date()
    except (ValueError, AttributeError):
        return None


def to_month_start(d) -> pd.Timestamp:
    """Return the first day of the month for any date-like input."""
    if not d:
        return pd.NaT
    ts = pd.to_datetime(d, errors='coerce')
    if pd.isna(ts):
        return pd.NaT
    return pd.Timestamp(ts.year, ts.month, 1)


def previous_month(d) -> pd.Timestamp:
    """Return the first day of the month preceding d."""
    d = to_month_start(d)
    return pd.NaT if pd.isna(d) else d - relativedelta(months=1)


# ── Index data loader ───────────────────────────────────────────
def get_item_index_df(item) -> pd.DataFrame:
    """
    Build a date-indexed DataFrame of all indices for *item*.
    Loads from DB on every call - use get_item_index_df_cached for hot paths.
    """
    from ..models import ItemIndex

    rows = (
        ItemIndex.query
        .filter_by(item_id=item.id)
        .order_by(ItemIndex.month.asc())
        .all()
    )
    if not rows:
        return pd.DataFrame()

    data = []
    for r in rows:
        try:
            idx = json.loads(r.indices_json or '{}')
        except (ValueError, TypeError):
            idx = {}
        row = {'date': pd.Timestamp(r.month.year, r.month.month, 1)}
        row.update(idx)
        data.append(row)

    df = pd.DataFrame(data)
    if df.empty:
        return df
    return df.set_index('date').sort_index()


@lru_cache(maxsize=64)
def _cached_index_df(item_id: int) -> pd.DataFrame:
    """
    LRU-cached version - keyed by item_id integer.
    Call invalidate_index_cache() after updating ItemIndex rows.
    """
    from ..models import Item
    item = Item.query.get(item_id)
    if item is None:
        return pd.DataFrame()
    return get_item_index_df(item)


def get_item_index_df_cached(item) -> pd.DataFrame:
    """Return cached index DataFrame for item."""
    return _cached_index_df(item.id)


def invalidate_index_cache():
    """Call this after any ItemIndex create/update/delete."""
    _cached_index_df.cache_clear()


# ── Index row lookup ───────────────────────────────────────────
def ieema_row(df: pd.DataFrame, dt, previous: bool = False):
    """
    Return latest index row on or before the target month.
    If previous=True, shift target back by one month (current-date rule).
    """
    if df is None or df.empty:
        return None
    target = previous_month(dt) if previous else to_month_start(dt)
    if pd.isna(target):
        return None
    eligible = df[df.index <= target]
    return eligible.iloc[-1] if not eligible.empty else None


# ── LD calculation ────────────────────────────────────────────
def calc_ld(scheduled_date: str, supply_date: str):
    """
    Returns (delay_days, ld_weeks, ld_rate_pct, ld_applicable).
    LD rate = 0.5% per week of delay, capped at 10%.
    """
    delay_days  = 0
    ld_weeks    = 0
    ld_rate_pct = 0.0
    ld_applicable = False

    due_ts    = pd.to_datetime(scheduled_date, errors='coerce')
    supply_ts = pd.to_datetime(supply_date,    errors='coerce')

    if pd.notna(due_ts) and pd.notna(supply_ts) and supply_ts > due_ts:
        delay_days    = int((supply_ts - due_ts).days)
        ld_weeks      = math.ceil(delay_days / 7)
        ld_rate_pct   = min(ld_weeks * 0.5, 10.0)
        ld_applicable = True

    return delay_days, ld_weeks, ld_rate_pct, ld_applicable


# ── PVCInput normaliser ────────────────────────────────────────
class PVCInput:
    """Normalises raw form data into typed attributes."""

    _KNOWN = {
        'itemid', 'item_id', 'basicrate', 'quantity', 'freightrateperunit',
        'pvcbasedate', 'origdp', 'refixeddp', 'extendeddp', 'caldate',
        'supdate', 'lowerrate', 'lowerfreight', 'lowerbasicdate',
        'rateapplied', 'tenderid', 'tender_id',
    }

    def __init__(self, form):
        self.user_id  = None
        self.username = None
        self.item_id  = int(form.get('itemid') or form.get('item_id') or 0)
        self.basic_rate          = safe_float(form.get('basicrate'))
        self.quantity            = safe_float(form.get('quantity'))
        self.freight_rate_per_unit = safe_float(form.get('freightrateperunit'))
        self.pvc_base_date       = form.get('pvcbasedate')
        self.original_dp         = form.get('origdp')
        self.refixed_dp          = form.get('refixeddp')
        self.extended_dp         = form.get('extendeddp')
        self.cal_date            = form.get('caldate')
        self.supply_date         = form.get('supdate')
        self.lower_rate          = safe_float(form.get('lowerrate'))
        self.lower_freight       = safe_float(form.get('lowerfreight'))
        self.lower_basic_date    = form.get('lowerbasicdate')
        self.rate_applied        = form.get('rateapplied')
        self.tender_id           = form.get('tenderid') or form.get('tender_id')
        self.extra_data = {
            k: form.get(k) for k in form.keys() if k not in self._KNOWN
        }

    def validate(self) -> list[str]:
        """Return list of error strings; empty list means valid."""
        errors = []
        if not self.item_id:
            errors.append('Please select an item.')
        if not self.pvc_base_date:
            errors.append('PVC base date is required.')
        if not self.cal_date:
            errors.append('Calculation date is required.')
        if not self.rate_applied:
            errors.append('Rate applied selection is required.')
        return errors

    def to_dict(self) -> dict:
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
