"""Deterministic comparison and market-alert rules; no model arithmetic."""
from datetime import date
from decimal import Decimal


def assess(promise, outcome, as_of):
    if date.fromisoformat(as_of) < date.fromisoformat(promise['period_end']):
        return {'status': 'pending', 'reason': 'The guided reporting period has not ended.', 'delta_pp': None}
    if not outcome or outcome.get('value') is None or not outcome.get('published_at') or outcome['published_at'] > as_of:
        return {'status': 'insufficient_evidence', 'reason': 'No reported outcome is available as of this date.', 'delta_pp': None}
    for key in ('metric', 'period', 'unit', 'basis', 'scope'):
        if promise.get(key) != outcome.get(key):
            return {'status': 'not_comparable', 'reason': f'Mismatched {key}; no verdict calculated.', 'delta_pp': None}
    actual, low, high = (Decimal(str(v)) for v in (outcome['value'], promise['low'], promise['high']))
    if not all(v.is_finite() for v in (actual, low, high)) or low > high:
        raise ValueError('Invalid numeric range')
    if actual < low:
        return {'status': 'missed', 'reason': 'Below the lower end of guidance.', 'delta_pp': float(actual - low)}
    if actual > high:
        return {'status': 'exceeded', 'reason': 'Above the upper end of guidance.', 'delta_pp': float(actual - high)}
    return {'status': 'met', 'reason': 'Within the guided range.', 'delta_pp': 0}


def market_alert(closes, volumes, price_threshold=3, volume_threshold=2, lookback=20):
    if price_threshold <= 0 or volume_threshold <= 0 or lookback < 1:
        raise ValueError('Thresholds and lookback must be positive')
    if len(closes) < lookback + 1 or len(volumes) < lookback + 1:
        return {'status': 'insufficient_history'}
    prior_close = closes[-2]
    average = sum(volumes[-lookback-1:-1]) / lookback
    if prior_close <= 0 or average <= 0:
        return {'status': 'insufficient_history'}
    move = (closes[-1] / prior_close - 1) * 100
    multiple = volumes[-1] / average
    return {'status': 'ok', 'price_change_pct': round(move, 4), 'volume_multiple': round(multiple, 4), 'price_triggered': abs(move) >= price_threshold, 'volume_triggered': multiple >= volume_threshold, 'lookback': lookback}
