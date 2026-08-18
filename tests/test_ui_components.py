"""
Tests for ui_components.

Widget factories need a Tk root, so those tests are skipped when no display is
available (e.g. headless CI). The palette wiring is asserted unconditionally.
"""
import pytest

import ui_components
from theme import GRAY_400, GRAY_500, GRAY_800, WHITE
from ui_components import (
    BUTTON_STYLES,
    ROW_EVEN,
    ROW_ODD,
    STATUS_COLORS,
    make_action_button,
    make_status_bar,
    make_toolbar_button,
)

ctk = ui_components.ctk


# ── re-exported palette ────────────────────────────────────────────────────

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


@pytest.mark.parametrize('style', list(BUTTON_STYLES))
def test_button_styles_are_hex_triples(style):
    colors = BUTTON_STYLES[style]
    assert len(colors) == 3
    assert all(c.startswith('#') and len(c) == 7 for c in colors)


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
    assert button.cget('fg_color') == GRAY_800
    assert button.cget('text_color') == WHITE
    assert button.cget('corner_radius') == 2
    assert button.cget('height') == 30


def test_make_action_button_secondary_style(root):
    button = make_action_button(root, 'Cancel', style='secondary')
    fg_color, hover_color, text_color = BUTTON_STYLES['secondary']
    assert button.cget('fg_color') == fg_color
    assert button.cget('hover_color') == hover_color
    assert button.cget('text_color') == text_color


def test_make_action_button_unknown_style_raises(root):
    with pytest.raises(KeyError):
        make_action_button(root, 'Odd', style='nonsense')


def test_make_action_button_binds_command(root):
    calls = []
    button = make_action_button(root, 'Click', command=lambda: calls.append(1))
    button.invoke()
    assert calls == [1]


def test_make_toolbar_button_defaults(root):
    button = make_toolbar_button(root, 'Load File')
    assert button.cget('fg_color') == BUTTON_STYLES['toolbar'][0]
    assert button.cget('width') == 110
    assert button.cget('height') == 32


@pytest.mark.parametrize('style', ['start', 'pause', 'toolbar_muted'])
def test_make_toolbar_button_styles(root, style):
    button = make_toolbar_button(root, style, style=style)
    assert button.cget('fg_color') == BUTTON_STYLES[style][0]


def test_make_toolbar_button_muted_text_color(root):
    button = make_toolbar_button(root, 'Errors Only', style='toolbar_muted')
    assert button.cget('text_color') == GRAY_400


def test_make_toolbar_button_forwards_width_and_kwargs(root):
    button = make_toolbar_button(root, 'Pause', style='pause', width=90, state='disabled')
    assert button.cget('width') == 90
    assert button.cget('state') == 'disabled'


def test_make_status_bar_defaults(root):
    label = make_status_bar(root)
    assert isinstance(label, ctk.CTkLabel)
    assert label.cget('text') == 'Ready — Load a file to begin.'
    assert label.cget('text_color') == GRAY_500
    assert label.cget('anchor') == 'w'
