"""
ui_components.py — Reusable CustomTkinter components for LinkGuard.
"""

import customtkinter as ctk

from theme import (
    AMBER,
    AMBER_DARK,
    FONT_BODY,
    FONT_BODY_BOLD,
    FONT_SMALL,
    GRAY_200,
    GRAY_300,
    GRAY_400,
    GRAY_500,
    GRAY_600,
    GRAY_700,
    GRAY_800,
    GRAY_900,
    GREEN,
    GREEN_DARK,
    ROW_EVEN,
    ROW_ODD,
    STATUS_COLORS,
    WHITE,
)

__all__ = [
    "STATUS_COLORS",
    "ROW_ODD",
    "ROW_EVEN",
    "make_action_button",
    "make_toolbar_button",
    "make_status_bar",
]


# Flat button palettes: style -> (fg_color, hover_color, text_color)
BUTTON_STYLES = {
    "primary": (GRAY_800, GRAY_900, WHITE),
    "secondary": (GRAY_200, GRAY_300, GRAY_800),
    "toolbar": (GRAY_700, GRAY_600, WHITE),
    "toolbar_muted": (GRAY_700, GRAY_600, GRAY_400),
    "start": (GREEN, GREEN_DARK, WHITE),
    "pause": (AMBER, AMBER_DARK, WHITE),
}


def _make_button(parent, text, command, style, **kwargs) -> ctk.CTkButton:
    fg_color, hover_color, text_color = BUTTON_STYLES[style]
    options = {
        "corner_radius": 2,
        "font": FONT_BODY_BOLD,
        "height": 30,
    }
    options.update(kwargs)
    return ctk.CTkButton(
        parent,
        text=text,
        command=command,
        fg_color=fg_color,
        hover_color=hover_color,
        text_color=text_color,
        **options,
    )


def make_action_button(parent, text: str, command=None, style: str = "primary") -> ctk.CTkButton:
    """
    Flat button matching DESIGN.md spec.
    style: 'primary' (dark bg) | 'secondary' (light bg)
    """
    return _make_button(parent, text, command, style)


def make_toolbar_button(parent, text: str, command=None, style: str = "toolbar",
                        width: int = 110, **kwargs) -> ctk.CTkButton:
    """Flat button sized for the dark top bar."""
    return _make_button(parent, text, command, style,
                        width=width, height=32, font=FONT_BODY, **kwargs)


def make_status_bar(parent) -> ctk.CTkLabel:
    """Bottom status bar label."""
    return ctk.CTkLabel(
        parent,
        text="Ready — Load a file to begin.",
        font=FONT_SMALL,
        text_color=GRAY_500,
        anchor="w",
    )
