import logging
import os
import sqlite3
from contextlib import closing

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'linkguard.db')
logger = logging.getLogger(__name__)


def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    with closing(sqlite3.connect(DB_PATH)) as conn:
        try:
            cur = conn.cursor()
            cur.execute('''
                CREATE TABLE IF NOT EXISTS scan_history (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    url         TEXT    NOT NULL,
                    status_code INTEGER,
                    latency_ms  REAL,
                    state       TEXT,
                    timestamp   DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            cur.execute('''
                CREATE TABLE IF NOT EXISTS app_settings (
                    key   TEXT PRIMARY KEY,
                    value TEXT
                )
            ''')
            conn.commit()
        except Exception:
            logger.exception('Failed to initialize database at %s', DB_PATH)
            try:
                conn.rollback()
            except Exception:
                logger.exception('Failed to roll back database initialization')
            raise


def insert_result(url, status_code, latency_ms, state):
    with closing(sqlite3.connect(DB_PATH)) as conn:
        try:
            conn.execute(
                'INSERT INTO scan_history (url, status_code, latency_ms, state) VALUES (?, ?, ?, ?)',
                (url, status_code, round(latency_ms, 2), state)
            )
            conn.commit()
        except Exception:
            logger.exception('Failed to insert scan result for %s', url)
            try:
                conn.rollback()
            except Exception:
                logger.exception('Failed to roll back scan result for %s', url)
            raise


def get_setting(key, default=None):
    with closing(sqlite3.connect(DB_PATH)) as conn:
        row = conn.execute('SELECT value FROM app_settings WHERE key=?', (key,)).fetchone()
    return row[0] if row else default


def set_setting(key, value):
    with closing(sqlite3.connect(DB_PATH)) as conn:
        try:
            conn.execute('INSERT OR REPLACE INTO app_settings (key, value) VALUES (?, ?)', (key, value))
            conn.commit()
        except Exception:
            logger.exception('Failed to save setting %s', key)
            try:
                conn.rollback()
            except Exception:
                logger.exception('Failed to roll back setting %s', key)
            raise


def load_config():
    with closing(sqlite3.connect(DB_PATH)) as conn:
        rows = conn.execute('SELECT key, value FROM app_settings').fetchall()
    return dict(rows)


if __name__ == '__main__':
    init_db()
    print(f'DB initialised at {os.path.abspath(DB_PATH)}')
