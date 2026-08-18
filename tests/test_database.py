import sqlite3
import pytest
import database


@pytest.fixture(autouse=True)
def temp_db(tmp_path, monkeypatch):
    db_path = str(tmp_path / 'test.db')
    monkeypatch.setattr(database, 'DB_PATH', db_path)
    database.init_db()
    yield db_path


def test_init_creates_tables(temp_db):
    conn = sqlite3.connect(temp_db)
    tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert 'scan_history' in tables
    assert 'app_settings' in tables
    conn.close()


def test_insert_result(temp_db):
    database.insert_result('https://example.com', 200, 123.4, 'Healthy')
    conn = sqlite3.connect(temp_db)
    row = conn.execute('SELECT * FROM scan_history').fetchone()
    conn.close()
    assert row[1] == 'https://example.com'
    assert row[2] == 200
    assert row[4] == 'Healthy'


def test_get_set_setting(temp_db):
    database.set_setting('theme', 'dark')
    assert database.get_setting('theme') == 'dark'


def test_get_setting_default(temp_db):
    assert database.get_setting('nonexistent', 'fallback') == 'fallback'


def test_load_config(temp_db):
    database.set_setting('key1', 'val1')
    database.set_setting('key2', 'val2')
    cfg = database.load_config()
    assert cfg['key1'] == 'val1'
    assert cfg['key2'] == 'val2'
