"""
theme.py -- Single source of truth for colors, fonts and result-state naming.
"""

# ── Result states ──────────────────────────────────────────────────────────
STATE_HEALTHY = "Healthy"
STATE_REDIRECT = "Redirect"
STATE_BROKEN = "Broken"
STATE_TIMEOUT = "Timeout"
STATE_ERROR = "Error"
STATE_UNKNOWN = "Unknown"

# States that count as a failed link (grid filter, error tally).
ERROR_STATES = (STATE_BROKEN, STATE_ERROR, STATE_TIMEOUT)

# ── Palette ────────────────────────────────────────────────────────────────
GREEN = "#10B981"
GREEN_DARK = "#059669"
AMBER = "#F59E0B"
AMBER_DARK = "#D97706"
RED = "#EF4444"
GRAY_900 = "#111827"
GRAY_800 = "#1F2937"
GRAY_700 = "#374151"
GRAY_600 = "#4B5563"
GRAY_500 = "#6B7280"
GRAY_400 = "#9CA3AF"
GRAY_300 = "#D1D5DB"
GRAY_200 = "#E5E7EB"
GRAY_100 = "#F3F4F6"
GRAY_50 = "#F9FAFB"
WHITE = "#FFFFFF"
BLUE_100 = "#DBEAFE"

STATUS_COLORS = {
    STATE_HEALTHY: GREEN,
    STATE_REDIRECT: AMBER,
    STATE_BROKEN: RED,
    STATE_TIMEOUT: RED,
    STATE_ERROR: RED,
    "Server Error": RED,
    STATE_UNKNOWN: GRAY_400,
}

ROW_ODD = WHITE
ROW_EVEN = GRAY_50

# ── Typography ─────────────────────────────────────────────────────────────
FONT_FAMILY = "Segoe UI"
FONT_BODY = (FONT_FAMILY, 12)
FONT_BODY_BOLD = (FONT_FAMILY, 12, "bold")
FONT_SMALL = (FONT_FAMILY, 11)
FONT_TABLE = (FONT_FAMILY, 10)
FONT_TABLE_BOLD = (FONT_FAMILY, 10, "bold")


def is_error_state(state: str) -> bool:
    """True when a result state represents a broken/failed link."""
    return state in ERROR_STATES


def state_color(state: str) -> str:
    """Foreground color for a result state."""
    return STATUS_COLORS.get(state, STATUS_COLORS[STATE_UNKNOWN])
