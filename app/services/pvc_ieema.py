"""
IEEMA PVC percentage calculations.
Used by all items whose pvc_formula_code is NOT 'IGBTPROPULSIONSYSTEM'.
"""
import pandas as pd

from . import GST_FACTOR
from .helpers import (
    safe_float, safe_round,
    ieema_row, calc_ld, get_item_index_df_cached,
)
from .scenarios import select_scenario


def pvc_percent(
    base_date: str,
    current_date: str,
    idx_df: pd.DataFrame,
    weights: dict,
) -> float:
    """
    Calculate the overall PVC % for a single base/current date pair.

    Formula:  sum over each index key of  weight * (current - base) / base
    """
    base = ieema_row(idx_df, base_date,    previous=False)
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


def pvc_percent_detailed(
    base_date: str,
    current_date: str,
    idx_df: pd.DataFrame,
    scenario: str,
    weights: dict,
) -> dict | None:
    """
    Same as pvc_percent but returns a rich dict including per-index breakdown.
    Returns None if index rows are missing.
    """
    base = ieema_row(idx_df, base_date,    previous=False)
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
        row[f'{key}_base']           = safe_round(b, 2) if b is not None else None
        row[f'{key}_current']        = safe_round(c, 2) if c is not None else None
        row[f'{key}_weight']         = weight
        row[f'{key}_contributionpct']= contrib
    row['pvcpercent'] = round(total, 4)
    return row


def calc_single_record(data: dict, idx_df: pd.DataFrame, weights: dict) -> dict:
    """
    Full IEEMA PVC calculation for one record.
    Returns a flat result dict compatible with PVCResult model and templates.
    """
    pvc_base_date   = data.get('pvcbasedate')
    cal_date        = data.get('caldate')
    orig_dp         = data.get('origdp')
    refixed_dp      = data.get('refixeddp')
    extended_dp     = data.get('extendeddp')
    scheduled_date  = extended_dp or refixed_dp or orig_dp
    supply_date     = data.get('supdate')
    lower_basic_date= data.get('lowerbasicdate')

    qty              = safe_float(data.get('quantity'))
    basic_rate       = safe_float(data.get('basicrate'))
    freight_rate_pu  = safe_float(data.get('freightrateperunit'))
    lower_rate       = safe_float(data.get('lowerrate'))
    lower_freight    = safe_float(data.get('lowerfreight'))

    freight_total        = freight_rate_pu * qty
    lower_freight_total  = lower_freight   * qty

    # ── PVC percentages per scenario ─────────────────────────────
    pct_a2 = pvc_percent(pvc_base_date,    cal_date,       idx_df, weights)
    pct_b2 = pvc_percent(pvc_base_date,    scheduled_date, idx_df, weights)
    pct_c1 = pvc_percent(lower_basic_date, cal_date,       idx_df, weights) if lower_basic_date else None
    pct_d1 = pvc_percent(lower_basic_date, scheduled_date, idx_df, weights) if lower_basic_date else None

    # ── Amount with PVC applied ─────────────────────────────────
    base_amt  = basic_rate  * qty
    lower_amt = lower_rate  * qty

    pvc_actual       = (base_amt  * (1 + pct_a2 / 100.0)          + freight_total)       * GST_FACTOR
    pvc_contractual  = (base_amt  * (1 + pct_b2 / 100.0)          + freight_total)       * GST_FACTOR
    lower_actual     = (lower_amt * (1 + (pct_c1 or 0) / 100.0)   + lower_freight_total) * GST_FACTOR if lower_rate else None
    lower_contractual= (lower_amt * (1 + (pct_d1 or 0) / 100.0)   + lower_freight_total) * GST_FACTOR if lower_rate else None

    # ── LD ──────────────────────────────────────────────────────
    delay_days, ld_weeks, ld_rate_pct, ld_applicable = calc_ld(scheduled_date, supply_date)
    ldamt_actual      = max(pvc_actual, 0)      * ld_rate_pct / 100.0 if ld_applicable else 0.0
    ldamt_contractual = max(pvc_contractual, 0) * ld_rate_pct / 100.0 if ld_applicable else 0.0

    pvc_actual_less_ld       = pvc_actual      - ldamt_actual
    pvc_contractual_less_ld  = pvc_contractual - ldamt_contractual
    lower_actual_less_ld     = lower_actual      - ldamt_actual      if lower_actual      is not None else None
    lower_contractual_less_ld= lower_contractual - ldamt_contractual if lower_contractual is not None else None

    # ── Scenario selection ─────────────────────────────────────
    rate_applied = data.get('rateapplied', '')
    selected, fair_price, candidates = select_scenario(
        rate_applied,
        pvc_actual, pvc_contractual,
        lower_actual, lower_contractual,
        pvc_actual_less_ld, pvc_contractual_less_ld,
        lower_actual_less_ld, lower_contractual_less_ld,
    )

    scenario_amounts = {
        'A2': safe_round(pvc_actual_less_ld),
        'B2': safe_round(pvc_contractual_less_ld),
    }
    if lower_rate:
        scenario_amounts['C1'] = safe_round(lower_actual)
        scenario_amounts['D1'] = safe_round(lower_contractual)

    # ── Index-wise detail for each scenario ──────────────────────
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
        'loweractual':             safe_round(lower_actual)      if lower_actual      is not None else None,
        'lowercontractual':        safe_round(lower_contractual) if lower_contractual is not None else None,
        'delaydays':               delay_days,
        'ldweeksnew':              ld_weeks,
        'ldratepctnew':            safe_round(ld_rate_pct),
        'ldapplicable':            ld_applicable,
        'ldamtactual':             safe_round(ldamt_actual),
        'ldamtcontractual':        safe_round(ldamt_contractual),
        'pvcactuallessldnew':      safe_round(pvc_actual_less_ld),
        'pvccontractuallessldnew': safe_round(pvc_contractual_less_ld),
        'loweractuallessld':       safe_round(lower_actual_less_ld)      if lower_actual_less_ld      is not None else None,
        'lowercontractuallessld':  safe_round(lower_contractual_less_ld) if lower_contractual_less_ld is not None else None,
        'fairpricenew':            safe_round(fair_price),
        'selectedscenarionew':     selected,
        'pvcperseta2':             safe_round(base_amt  * pct_a2 / 100.0),
        'pvcpersetb2':             safe_round(base_amt  * pct_b2 / 100.0),
        'pvcpersetc1':             safe_round(lower_amt * (pct_c1 or 0) / 100.0) if lower_rate else None,
        'pvcpersetd1':             safe_round(lower_amt * (pct_d1 or 0) / 100.0) if lower_rate else None,
        'scenarioamounts':         scenario_amounts,
        'scenariodetails':         scenario_details,
        'igbt_vendor_details':     [],
        'igbt_index_details':      [],
        'tenderno':                None,
        'pono':                    None,
    }
