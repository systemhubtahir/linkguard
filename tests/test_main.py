"""
Tests for LinkGuardApp logic in main.py.

The app subclasses ctk.CTk, so instances are built with object.__new__ and the
widgets/state the tested methods touch are replaced with mocks. This exercises
the controller logic (loading, scanning, filtering, exporting, result handling)
without needing a display.
"""
import queue
import threading
from unittest.mock import MagicMock, patch

import pytest

import main
from main import LinkGuardApp
from theme import GRAY_400, RED


def _result(url='https://example.com', status_code=200, latency_ms=100.0, state='Healthy'):
    return {'url': url, 'status_code': status_code, 'latency_ms': latency_ms, 'state': state}


@pytest.fixture
def app():
    app = object.__new__(LinkGuardApp)
    app._urls = []
    app._results = []
    app._scan_queue = queue.Queue()
    app._pause_event = threading.Event()
    app._cancel_event = threading.Event()
    app._scan_thread = None
    app._total = 0
    app._scanned = 0
    app._errors = 0
    app._filter_errors_only = False
    app.tree = MagicMock()
    app.tree.get_children.return_value = ()
    app.btn_start = MagicMock()
    app.btn_pause = MagicMock()
    app.btn_filter = MagicMock()
    app.status_label = MagicMock()
    return app


# ── _state_of / _is_visible ────────────────────────────────────────────────

def test_state_of_defaults_to_unknown(app):
    assert app._state_of({'url': 'https://a.com'}) == 'Unknown'
    assert app._state_of(_result(state='Broken')) == 'Broken'


@pytest.mark.parametrize('state,visible', [
    ('Healthy', False),
    ('Redirect', False),
    ('Broken', True),
    ('Error', True),
    ('Timeout', True),
])
def test_is_visible_while_filtering(app, state, visible):
    app._filter_errors_only = True
    assert app._is_visible(state) is visible


def test_is_visible_without_filter_shows_everything(app):
    assert all(app._is_visible(s) for s in ('Healthy', 'Redirect', 'Broken', 'Unknown'))


# ── _set_status ────────────────────────────────────────────────────────────

def test_set_status_updates_label(app):
    app._set_status('hello')
    app.status_label.configure.assert_called_once_with(text='hello')


# ── _load_file ─────────────────────────────────────────────────────────────

def test_load_file_populates_urls(app):
    with patch.object(main.filedialog, 'askopenfilename', return_value='/tmp/urls.txt'), \
         patch.object(main, 'parse_file', return_value=['https://a.com', 'https://b.com']) as parse:
        app._load_file()
    parse.assert_called_once_with('/tmp/urls.txt')
    assert app._urls == ['https://a.com', 'https://b.com']
    assert app._total == 2
    assert 'Loaded 2 URLs' in app.status_label.configure.call_args.kwargs['text']


def test_load_file_cancelled_keeps_state(app):
    app._urls = ['https://kept.com']
    with patch.object(main.filedialog, 'askopenfilename', return_value=''), \
         patch.object(main, 'parse_file') as parse:
        app._load_file()
    parse.assert_not_called()
    assert app._urls == ['https://kept.com']
    assert app._total == 0


# ── _start_scan ────────────────────────────────────────────────────────────

def test_start_scan_without_urls_warns(app):
    with patch.object(main.messagebox, 'showwarning') as warn, \
         patch.object(main.threading, 'Thread') as thread:
        app._start_scan()
    warn.assert_called_once()
    thread.assert_not_called()


def test_start_scan_starts_thread_and_resets_counters(app):
    app._urls = ['https://a.com']
    app._results = [_result()]
    app._scanned = 5
    app._errors = 3
    app._pause_event.set()
    app._cancel_event.set()

    with patch.object(main.threading, 'Thread') as Thread:
        app._start_scan()

    Thread.assert_called_once()
    kwargs = Thread.call_args.kwargs
    assert kwargs['target'] is main.run_scan
    assert kwargs['args'] == (app._urls, app._scan_queue.put,
                              app._pause_event, app._cancel_event)
    assert kwargs['daemon'] is True
    Thread.return_value.start.assert_called_once()

    assert app._results == []
    assert app._scanned == 0
    assert app._errors == 0
    assert not app._pause_event.is_set()
    assert not app._cancel_event.is_set()
    app.btn_start.configure.assert_called_once_with(state='disabled')
    app.btn_pause.configure.assert_called_once_with(text='Pause', state='normal')
    app.tree.delete.assert_not_called()  # no existing rows


def test_start_scan_ignored_while_scan_running(app):
    app._urls = ['https://a.com']
    app._scan_thread = MagicMock()
    app._scan_thread.is_alive.return_value = True

    with patch.object(main.threading, 'Thread') as Thread:
        app._start_scan()

    Thread.assert_not_called()


# ── _pause_scan ────────────────────────────────────────────────────────────

def test_pause_scan_sets_pause_event(app):
    app._pause_scan()
    assert app._pause_event.is_set()
    assert not app._cancel_event.is_set()  # pausing must not kill the scan
    app.btn_pause.configure.assert_called_once_with(text='Resume')


def test_pause_scan_toggles_back_to_resume(app):
    app._pause_event.set()
    app._pause_scan()
    assert not app._pause_event.is_set()
    app.btn_pause.configure.assert_called_once_with(text='Pause')


# ── _on_close ──────────────────────────────────────────────────────────────

def test_on_close_cancels_scan_and_destroys(app):
    app._pause_event.set()
    app.destroy = MagicMock()
    app._on_close()
    assert app._cancel_event.is_set()
    assert not app._pause_event.is_set()  # unblock a paused worker so it can exit
    app.destroy.assert_called_once_with()


# ── _toggle_filter ─────────────────────────────────────────────────────────

def test_toggle_filter_enables_and_redraws(app):
    app._results = [_result(state='Healthy'), _result(url='https://x.com', state='Broken')]
    app._toggle_filter()
    assert app._filter_errors_only is True
    app.btn_filter.configure.assert_called_once_with(text_color=RED)
    # only the broken row is re-inserted
    assert app.tree.insert.call_count == 1
    assert app.tree.insert.call_args.kwargs['values'][1] == 'https://x.com'


def test_toggle_filter_disables_and_shows_all(app):
    app._filter_errors_only = True
    app._results = [_result(state='Healthy'), _result(url='https://x.com', state='Broken')]
    app._toggle_filter()
    assert app._filter_errors_only is False
    app.btn_filter.configure.assert_called_once_with(text_color=GRAY_400)
    assert app.tree.insert.call_count == 2


# ── _export ────────────────────────────────────────────────────────────────

def test_export_without_results_warns(app):
    with patch.object(main.messagebox, 'showwarning') as warn, \
         patch.object(main, 'export_csv') as export:
        app._export()
    warn.assert_called_once()
    export.assert_not_called()


def test_export_cancelled_dialog_does_nothing(app):
    app._results = [_result()]
    with patch.object(main.filedialog, 'asksaveasfilename', return_value=''), \
         patch.object(main, 'export_csv') as export:
        app._export()
    export.assert_not_called()


def test_export_writes_and_reports_status(app):
    app._results = [_result(), _result(url='https://b.com')]
    with patch.object(main.filedialog, 'asksaveasfilename', return_value='/tmp/out/report.csv'), \
         patch.object(main, 'export_csv') as export:
        app._export()
    export.assert_called_once_with(app._results, '/tmp/out/report.csv')
    text = app.status_label.configure.call_args.kwargs['text']
    assert 'Exported 2 rows' in text
    assert 'report.csv' in text


def test_export_failure_shows_error(app):
    app._results = [_result()]
    with patch.object(main.filedialog, 'asksaveasfilename', return_value='/tmp/report.csv'), \
         patch.object(main, 'export_csv', side_effect=OSError('disk full')), \
         patch.object(main.messagebox, 'showerror') as error:
        app._export()
    error.assert_called_once_with('Export failed', 'disk full')


# ── _handle_result ─────────────────────────────────────────────────────────

def test_handle_result_records_and_persists(app):
    app._total = 2
    with patch.object(main, 'insert_result') as insert:
        app._handle_result(_result())
    insert.assert_called_once_with('https://example.com', 200, 100.0, 'Healthy')
    assert app._results == [_result()]
    assert app._scanned == 1
    assert app._errors == 0
    assert app.tree.insert.call_count == 1


@pytest.mark.parametrize('state,expected_errors', [
    ('Healthy', 0),
    ('Redirect', 0),
    ('Broken', 1),
    ('Error', 1),
    ('Timeout', 1),
])
def test_handle_result_error_counting(app, state, expected_errors):
    app._total = 5
    with patch.object(main, 'insert_result'):
        app._handle_result(_result(state=state))
    assert app._errors == expected_errors


def test_handle_result_defaults_missing_state_to_unknown(app):
    app._total = 2
    with patch.object(main, 'insert_result') as insert:
        app._handle_result({'url': 'https://a.com', 'status_code': 200, 'latency_ms': 5.0})
    assert insert.call_args.args[3] == 'Unknown'
    assert app._errors == 0


def test_handle_result_hides_healthy_rows_when_filtering(app):
    app._total = 2
    app._filter_errors_only = True
    with patch.object(main, 'insert_result'):
        app._handle_result(_result(state='Healthy'))
    app.tree.insert.assert_not_called()
    assert app._results  # still recorded, just not displayed


def test_handle_result_shows_error_rows_when_filtering(app):
    app._total = 2
    app._filter_errors_only = True
    with patch.object(main, 'insert_result'):
        app._handle_result(_result(state='Broken'))
    assert app.tree.insert.call_count == 1


def test_handle_result_progress_status(app):
    app._total = 3
    app._scan_thread = MagicMock()
    app._scan_thread.is_alive.return_value = True
    with patch.object(main, 'insert_result'):
        app._handle_result(_result(state='Broken'))
    text = app.status_label.configure.call_args.kwargs['text']
    assert 'Scanned: 1/3' in text
    assert 'Errors: 1' in text
    assert 'Active Threads: 2' in text


def test_handle_result_reports_zero_active_threads_when_thread_done(app):
    app._total = 3
    app._scan_thread = MagicMock()
    app._scan_thread.is_alive.return_value = False
    with patch.object(main, 'insert_result'):
        app._handle_result(_result())
    assert 'Active Threads: 0' in app.status_label.configure.call_args.kwargs['text']


def test_handle_result_finalizes_on_last_url(app):
    app._total = 1
    with patch.object(main, 'insert_result'):
        app._handle_result(_result(state='Broken'))
    app.btn_start.configure.assert_called_once_with(state='normal')
    app.btn_pause.configure.assert_called_once_with(state='disabled')
    assert 'Scan complete' in app.status_label.configure.call_args.kwargs['text']


# ── _insert_row / _clear_grid / _redraw_grid ───────────────────────────────

def test_insert_row_values_and_tags(app):
    app.tree.get_children.return_value = ()
    app._insert_row(_result(latency_ms=123.6, state='Redirect'))
    kwargs = app.tree.insert.call_args.kwargs
    assert kwargs['values'] == (1, 'https://example.com', 200, '124', 'Redirect')
    assert kwargs['tags'] == ('even', 'Redirect')
    app.tree.yview_moveto.assert_called_once_with(1)


def test_insert_row_zebra_alternates(app):
    app.tree.get_children.return_value = ('row1',)
    app._insert_row(_result())
    assert app.tree.insert.call_args.kwargs['tags'][0] == 'odd'


def test_insert_row_dashes_missing_status_code(app):
    app._insert_row(_result(status_code=None, latency_ms=10000, state='Timeout'))
    assert app.tree.insert.call_args.kwargs['values'][2] == '—'


def test_clear_grid_deletes_every_row(app):
    app.tree.get_children.return_value = ('a', 'b', 'c')
    app._clear_grid()
    assert [c.args[0] for c in app.tree.delete.call_args_list] == ['a', 'b', 'c']


def test_redraw_grid_reinserts_all_results(app):
    app._results = [_result(), _result(url='https://b.com', state='Broken')]
    app._redraw_grid()
    assert app.tree.insert.call_count == 2


def test_redraw_grid_defaults_missing_state_to_unknown(app):
    app._filter_errors_only = True
    app._results = [{'url': 'https://a.com', 'status_code': 200, 'latency_ms': 1.0}]
    app._redraw_grid()
    app.tree.insert.assert_not_called()


# ── _poll_queue ────────────────────────────────────────────────────────────

def test_poll_queue_drains_queue_and_reschedules(app):
    app.after = MagicMock()
    app._handle_result = MagicMock()
    app._scan_queue.put(_result())
    app._scan_queue.put(_result(url='https://b.com'))

    app._poll_queue()

    assert app._handle_result.call_count == 2
    app.after.assert_called_once_with(150, app._poll_queue)


def test_poll_queue_survives_handler_error(app):
    app.after = MagicMock()
    app._handle_result = MagicMock(side_effect=RuntimeError('boom'))
    app._scan_queue.put(_result())

    app._poll_queue()  # must not raise

    app.after.assert_called_once_with(150, app._poll_queue)


# ── real widget construction (needs a display) ─────────────────────────────

@pytest.fixture
def real_app(tmp_path, monkeypatch):
    monkeypatch.setattr(main, 'init_db', lambda: None)
    monkeypatch.setattr(main, 'load_config', lambda: {'theme': 'light'})
    try:
        instance = LinkGuardApp()
    except Exception as exc:  # pragma: no cover - depends on environment
        pytest.skip(f'Tk display unavailable: {exc}')
    yield instance
    instance.destroy()


def test_app_builds_widgets(real_app):
    assert real_app.title() == 'LinkGuard'
    assert real_app.tree['columns'] == ('id', 'url', 'status', 'latency', 'state')
    assert real_app.btn_start.cget('text') == 'Start Scan'
    assert real_app.btn_pause.cget('state') == 'disabled'
    assert 'Ready' in real_app.status_label.cget('text')


def test_app_initial_state(real_app):
    assert real_app._urls == []
    assert real_app._results == []
    assert real_app._total == real_app._scanned == real_app._errors == 0
    assert real_app._filter_errors_only is False
    assert not real_app._pause_event.is_set()
    assert not real_app._cancel_event.is_set()
    assert real_app.config == {'theme': 'light'}


def test_app_inserts_and_clears_real_rows(real_app):
    real_app._insert_row(_result())
    real_app._insert_row(_result(url='https://b.com', status_code=404, state='Broken'))
    assert len(real_app.tree.get_children()) == 2

    real_app._clear_grid()
    assert real_app.tree.get_children() == ()
