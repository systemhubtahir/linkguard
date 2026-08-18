"""
Tests for ui_components.

Widget factories need a Tk root, so those tests are skipped when no display is
available (e.g. headless CI). The colour constants are asserted unconditionally.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import pytest

import ui_components
from ui_components import ROW_EVEN, ROW_ODD, STATUS_COLORS, make_action_button, make_status_bar

ctk = ui_components.ctk


# ── constants ──────────────────────────────────────────────────────────────

def test_status_colors_cover_all_states():
    assert set(STATUS_COLORS) == {
        'Healthy', 'Redirect', 'Broken', 'Timeout', 'Error', 'Server Error', 'Unknown',
    }


@pytest.mark.parametrize('state', list(STATUS_COLORS))
def test_status_colors_are_hex(state):
    color = STATUS_COLORS[state]
    assert color.startswith('#') and len(color) == 7
    int(color[1:], 16)  # raises if not hex


def test_failure_states_share_red():
    assert STATUS_COLORS['Broken'] == STATUS_COLORS['Timeout'] == STATUS_COLORS['Error']


def test_zebra_rows_differ():
    assert ROW_ODD != ROW_EVEN


# ── widget factories ───────────────────────────────────────────────────────

@pytest.fixture
def root():
    try:
        window = ctk.CTk()
    except Exception as exc:  # pragma: no cover - depends on environment
        pytest.skip(f'Tk display unavailable: {exc}')
    yield window
    window.destroy()


def test_make_action_button_primary_defaults(root):
    button = make_action_button(root, 'Start Scan')
    assert isinstance(button, ctk.CTkButton)
    assert button.cget('text') == 'Start Scan'
    assert button.cget('fg_color') == '#1F2937'
    assert button.cget('text_color') == '#FFFFFF'
    assert button.cget('corner_radius') == 2
    assert button.cget('height') == 30


def test_make_action_button_secondary_style(root):
    button = make_action_button(root, 'Cancel', style='secondary')
    assert button.cget('fg_color') == '#E5E7EB'
    assert button.cget('text_color') == '#1F2937'
    assert button.cget('hover_color') == '#D1D5DB'


def test_make_action_button_unknown_style_falls_back_to_primary(root):
    button = make_action_button(root, 'Odd', style='nonsense')
    assert button.cget('fg_color') == '#1F2937'


def test_make_action_button_binds_command(root):
    calls = []
    button = make_action_button(root, 'Click', command=lambda: calls.append(1))
    button.invoke()
    assert calls == [1]


def test_make_status_bar_defaults(root):
    label = make_status_bar(root)
    assert isinstance(label, ctk.CTkLabel)
    assert label.cget('text') == 'Ready — Load a file to begin.'
    assert label.cget('text_color') == '#6B7280'
    assert label.cget('anchor') == 'w'
