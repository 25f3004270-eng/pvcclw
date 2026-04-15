"""
Centralised scenario selection logic shared by IEEMA and IGBT calculators.
"""
from . import (
    RATE_BEFORE_DUE, RATE_AFTER_DUE,
    RATE_LOWER, RATE_LOWER_LD, RATE_LOWER_LD_EXTENDED,
)


def select_scenario(
    rate_applied: str,
    pvc_actual: float,
    pvc_contractual: float,
    lower_actual,
    lower_contractual,
    pvc_actual_less_ld: float,
    pvc_contractual_less_ld: float,
    lower_actual_less_ld,
    lower_contractual_less_ld,
) -> tuple[str, float, dict]:
    """
    Choose the minimum-cost scenario given rate_applied.

    Returns:
        selected          : scenario key e.g. 'A2'
        fair_price        : the payable amount for that scenario
        candidates        : dict of {scenario_key: amount} that were compared
    """
    ra = (rate_applied or '').strip().lower()

    if ra == RATE_BEFORE_DUE:
        candidates = {'A2': pvc_actual}

    elif ra == RATE_AFTER_DUE:
        candidates = {
            'A2': pvc_actual_less_ld,
            'B2': pvc_contractual_less_ld,
        }

    elif ra == RATE_LOWER:
        candidates = {
            'A2': pvc_actual,
            'B2': pvc_contractual,
        }
        if lower_actual is not None:
            candidates['C1'] = lower_actual
        if lower_contractual is not None:
            candidates['D1'] = lower_contractual

    elif ra == RATE_LOWER_LD:
        candidates = {
            'A2': pvc_actual_less_ld,
            'B2': pvc_contractual_less_ld,
        }
        if lower_actual is not None:
            candidates['C1'] = lower_actual
        if lower_contractual is not None:
            candidates['D1'] = lower_contractual

    elif ra == RATE_LOWER_LD_EXTENDED:
        candidates = {
            'A2': pvc_actual_less_ld,
            'B2': pvc_contractual_less_ld,
        }
        if lower_actual_less_ld is not None:
            candidates['C1'] = lower_actual_less_ld
        if lower_contractual_less_ld is not None:
            candidates['D1'] = lower_contractual_less_ld

    else:
        # Default: all available amounts
        candidates = {
            'A2': pvc_actual,
            'B2': pvc_contractual,
        }
        if lower_actual is not None:
            candidates['C1'] = lower_actual
        if lower_contractual is not None:
            candidates['D1'] = lower_contractual

    # Remove None values before comparing
    candidates = {k: v for k, v in candidates.items() if v is not None}

    if not candidates:
        return 'A2', pvc_actual, {'A2': pvc_actual}

    selected   = min(candidates, key=candidates.get)
    fair_price = candidates[selected]
    return selected, fair_price, candidates
