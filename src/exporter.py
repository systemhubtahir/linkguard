import pandas as pd
import os
from datetime import datetime

FORMULA_PREFIXES = ('=', '+', '-', '@', '\t', '\r')


def _neutralise(value):
    """Prefix a quote to values a spreadsheet would evaluate as a formula."""
    if isinstance(value, str) and value.startswith(FORMULA_PREFIXES):
        return "'" + value
    return value


def export_csv(results, filepath=None):
    """
    results: list of dicts {url, status_code, latency_ms, state}
    filepath: full path. If None, auto-generate in exports/.
    Returns the path written to.
    """
    if not results:
        raise ValueError('No results to export.')

    if filepath is None:
        exports_dir = os.path.join(os.path.dirname(__file__), '..', 'exports')
        os.makedirs(exports_dir, exist_ok=True)
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        filepath = os.path.join(exports_dir, f'scan_{ts}.csv')

    df = pd.DataFrame(results, columns=['url', 'status_code', 'latency_ms', 'state'])
    for column in ('url', 'state'):
        df[column] = df[column].map(_neutralise)
    df.index += 1
    df.index.name = 'id'
    df['timestamp'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    df.to_csv(filepath)
    return filepath
