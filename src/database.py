import os
import sqlite3
from contextlib import contextmanager

from paths import ensure_dir, project_path

DB_PATH = project_path('data', 'linkguard.db')

SCHEMA = (
    '''
    CREATE TABLE IF NOT EXISTS scan_history (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        url         TEXT    NOT NULL,
        status_code INTEGER,
        latency_ms  REAL,
        state       TEXT,
        timestamp   DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    ''',
    '''
    CREATE TABLE IF NOT EXISTS app_settings (
        key   TEXT PRIMARY KEY,
        value TEXT
    )
    ''',
)


@contextmanager
def _connect(commit=False):
    """Open a connection to DB_PATH, optionally committing, always closing."""
    conn = sqlite3.connect(DB_PATH)
    try:
        yield conn
        if commit:
            conn.commit()
    finally:
        conn.close()


def init_db():
    ensure_dir(os.path.dirname(DB_PATH))
    with _connect(commit=True) as conn:
        for statement in SCHEMA:
            conn.execute(statement)


def insert_result(url, status_code, latency_ms, state):
    with _connect(commit=True) as conn:
        conn.execute(
            'INSERT INTO scan_history (url, status_code, latency_ms, state) VALUES (?, ?, ?, ?)',
            (url, status_code, round(latency_ms, 2), state)
        )


def get_setting(key, default=None):
    with _connect() as conn:
        row = conn.execute('SELECT value FROM app_settings WHERE key=?', (key,)).fetchone()
    return row[0] if row else default


def set_setting(key, value):
    with _connect(commit=True) as conn:
        conn.execute('INSERT OR REPLACE INTO app_settings (key, value) VALUES (?, ?)', (key, value))


def load_config():
    with _connect() as conn:
        rows = conn.execute('SELECT key, value FROM app_settings').fetchall()
    return dict(rows)


if __name__ == '__main__':
    init_db()
    print(f'DB initialised at {os.path.abspath(DB_PATH)}')
