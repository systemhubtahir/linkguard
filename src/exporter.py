import os
import pandas as pd
from datetime import datetime

from paths import ensure_dir, project_path

RESULT_COLUMNS = ['url', 'status_code', 'latency_ms', 'state']


def export_csv(results, filepath=None):
    """
    results: list of dicts {url, status_code, latency_ms, state}
    filepath: full path. If None, auto-generate in exports/.
    Returns the path written to.
    """
    if not results:
        raise ValueError('No results to export.')

    now = datetime.now()
    if filepath is None:
        exports_dir = ensure_dir(project_path('exports'))
        filepath = os.path.join(exports_dir, f"scan_{now.strftime('%Y%m%d_%H%M%S')}.csv")

    df = pd.DataFrame(results, columns=RESULT_COLUMNS)
    df.index += 1
    df.index.name = 'id'
    df['timestamp'] = now.strftime('%Y-%m-%d %H:%M:%S')
    df.to_csv(filepath)
    return filepath
