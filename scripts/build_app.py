"""Build a self-contained research app from the supplied, validated CSV artifacts.

No untrusted joblib or pickle files are loaded. No model is retrained by this
script. It verifies saved revenue values against the preserved Python engine.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from zephyrtrade.evaluate import realized_market_revenue  # noqa: E402
from zephyrtrade.optimize import validate_price_order  # noqa: E402

WEB = ROOT / 'src' / 'zephyrtrade' / 'web'
MODEL_NAMES = {
    'direct_regression': ('Direct continuous', 'Direct learning'),
    'direct_classification': ('Direct bid brackets', 'Direct learning'),
    'locally_weighted': ('Locally weighted linear', 'Forecast → optimise'),
    'polynomial_ols': ('Polynomial OLS', 'Forecast → optimise'),
    'ridge_polynomial': ('Polynomial Ridge', 'Forecast → optimise'),
    'clustered_ridge': ('Clustered Ridge', 'Forecast → optimise'),
    'linear_ols': ('Linear OLS', 'Forecast → optimise'),
    'lasso_polynomial': ('Polynomial Lasso', 'Forecast → optimise'),
    'persistence_24h': ('24-hour persistence', 'Baseline'),
}

def make_snapshot(root: Path = ROOT) -> dict:
    """Align both experiments and validate every observation and saved revenue."""
    paths = [root / 'artifacts/phase2/test_predictions.csv.gz',
             root / 'artifacts/phase3/test_direct_predictions.csv.gz']
    frames = [pd.read_csv(p) for p in paths]
    a, b = frames
    common = ['timestamp_utc', 'farm_id', 'actual_power_mw', 'capacity_mw',
              'day_ahead_price_dkk_mwh', 'up_reg_price_dkk_mwh', 'down_reg_price_dkk_mwh']
    if len(a) != len(b) or not a[common].equals(b[common]):
        raise ValueError('Phase 2 and 3 rows do not align exactly.')
    times = pd.to_datetime(a.timestamp_utc, utc=True, errors='raise')
    if times.duplicated().any() or not times.is_monotonic_increasing:
        raise ValueError('Timestamps must be unique and strictly increasing.')
    if a.farm_id.nunique() != 1:
        raise ValueError('This snapshot supports one evaluated farm, not an aggregated fleet.')
    for frame in frames:
        numeric = frame.select_dtypes(include='number')
        if not np.isfinite(numeric.to_numpy()).all():
            raise ValueError('Non-finite source values.')
    if a.capacity_mw.nunique() != 1 or a.capacity_mw.iloc[0] <= 0:
        raise ValueError('The snapshot requires one positive constant site capacity.')
    if (times.dt.minute != 0).any() or (times.dt.second != 0).any():
        raise ValueError('The snapshot requires hourly observations.')
    validate_price_order(a.day_ahead_price_dkk_mwh.to_numpy(), a.up_reg_price_dkk_mwh.to_numpy(), a.down_reg_price_dkk_mwh.to_numpy())
    if ((a.actual_power_mw < 0) | (a.actual_power_mw > a.capacity_mw)).any():
        raise ValueError('Actual output exceeds physical bounds.')
    models = []
    maximum_error = 0.
    for key, (name, family) in MODEL_NAMES.items():
        frame = b if key.startswith('direct_') else a
        offer = frame[f'{key}_offer_mw'].to_numpy()
        if not np.isfinite(offer).all() or (offer < 0).any() or (offer > a.capacity_mw).any():
            raise ValueError(f'Invalid offers for {key}.')
        revenue = realized_market_revenue(offer, a.actual_power_mw.to_numpy(),
                 a.day_ahead_price_dkk_mwh.to_numpy(), a.up_reg_price_dkk_mwh.to_numpy(),
                 a.down_reg_price_dkk_mwh.to_numpy())
        error = float(np.max(np.abs(revenue - frame[f'{key}_revenue_dkk'].to_numpy())))
        if error > 1e-7:
            raise ValueError(f'Saved revenue mismatch for {key}: {error}')
        maximum_error = max(maximum_error, error)
        model = {'id': key, 'name': name, 'family': family, 'offers': offer.tolist()}
        if f'{key}_prediction_mw' in frame:
            model['forecasts'] = frame[f'{key}_prediction_mw'].tolist()
        models.append(model)
    provenance = json.loads((root / 'data/raw/provenance.json').read_text())
    metadata = pd.read_csv(root / 'data/raw/farm_metadata.csv').to_dict(orient='records')
    site = next((x for x in metadata if x['farm_id'] == a.farm_id.iloc[0]), None)
    if site is None or site['capacity_mw'] != a.capacity_mw.iloc[0]:
        raise ValueError('Site metadata does not match the evaluated observations.')
    expected_hours = int((times.iloc[-1] - times.iloc[0]).total_seconds() / 3600) + 1
    snap = {'schema_version': 1, 'app_version': '1.1.0',
            'data_kind': 'Supplied synthetic research backtest',
            'farm_id': str(a.farm_id.iloc[0]), 'farm_name': site['display_name'],
            'capacity_mw': float(a.capacity_mw.iloc[0]), 'market_area': 'DK2',
            'currency': 'DKK', 'timezone': 'UTC', 'interval_hours': 1,
            'source_generated_at': provenance['generated_at_utc'],
            'timestamps': a.timestamp_utc.tolist(), 'actual': a.actual_power_mw.tolist(),
            'day_ahead': a.day_ahead_price_dkk_mwh.tolist(),
            'up': a.up_reg_price_dkk_mwh.tolist(), 'down': a.down_reg_price_dkk_mwh.tolist(),
            'models': models, 'farms': metadata,
            'quality': {'rows': len(a), 'expected_hours_between_endpoints': expected_hours,
                        'excluded_hours_between_endpoints': expected_hours-len(a),
                        'source_negative_price_rows_removed': provenance['price_filter']['negative_price_rows_removed'],
                        'revenue_values_checked': len(a)*len(models),
                        'maximum_revenue_error_dkk': maximum_error},
            'sources': [{'path': str(p.relative_to(root)), 'sha256': hashlib.sha256(p.read_bytes()).hexdigest()} for p in paths]}
    return snap


def build() -> None:
    """Write snapshot, provenance verification and the portable HTML artifact."""
    snap = make_snapshot()
    data = 'window.ZEPHYR_DATA = ' + json.dumps(snap, ensure_ascii=False, allow_nan=False, separators=(',', ':')).replace('</', '<\\/') + ';\n'
    (WEB / 'snapshot.js').write_text(data, encoding='utf-8')
    index = (WEB / 'index.html').read_text(encoding='utf-8')
    index = index.replace('<link rel="stylesheet" href="styles.css">', '<style>\n' + (WEB/'styles.css').read_text() + '\n</style>')
    for name in ['snapshot.js', 'engine.js', 'app.js']:
        content = (WEB/name).read_text(encoding='utf-8').replace('</script', '<\\/script')
        index = index.replace(f'<script src="{name}" defer></script>', '<script>\n' + content + '\n</script>')
    (ROOT / 'ZephyrTrade-Champion.html').write_text(index, encoding='utf-8')
    out = ROOT / 'docs/champion/evidence/snapshot-verification.json'
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({'status': 'PASS', 'quality': snap['quality'], 'sources': snap['sources']}, indent=2))
    print(json.dumps({'status': 'PASS', 'output': 'ZephyrTrade-Champion.html', 'rows':len(snap['timestamps']),
                      'models':len(snap['models']), **snap['quality']}, indent=2))

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    build()
