import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'linkguard.db')


def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
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
    conn.close()


def insert_result(url, status_code, latency_ms, state):
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        'INSERT INTO scan_history (url, status_code, latency_ms, state) VALUES (?, ?, ?, ?)',
        (url, status_code, round(latency_ms, 2), state)
    )
    conn.commit()
    conn.close()


def get_setting(key, default=None):
    conn = sqlite3.connect(DB_PATH)
    row = conn.execute('SELECT value FROM app_settings WHERE key=?', (key,)).fetchone()
    conn.close()
    return row[0] if row else default


def set_setting(key, value):
    conn = sqlite3.connect(DB_PATH)
    conn.execute('INSERT OR REPLACE INTO app_settings (key, value) VALUES (?, ?)', (key, value))
    conn.commit()
    conn.close()


def load_config():
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute('SELECT key, value FROM app_settings').fetchall()
    conn.close()
    return dict(rows)


if __name__ == '__main__':
    init_db()
    print(f'DB initialised at {os.path.abspath(DB_PATH)}')
