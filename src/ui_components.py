"""
ui_components.py — Reusable CustomTkinter components for LinkGuard.
"""

import customtkinter as ctk


# Status color map (foreground tag color for Treeview rows)
STATUS_COLORS = {
    "Healthy":      "#10B981",  # Green
    "Redirect":     "#F59E0B",  # Amber
    "Broken":       "#EF4444",  # Red
    "Timeout":      "#EF4444",
    "Error":        "#EF4444",
    "Server Error": "#EF4444",
    "Invalid":      "#9CA3AF",
    "Unknown":      "#9CA3AF",
}

ROW_ODD  = "#FFFFFF"
ROW_EVEN = "#F9FAFB"


def make_action_button(parent, text: str, command=None, style: str = "primary") -> ctk.CTkButton:
    """
    Flat button matching DESIGN.md spec.
    style: 'primary' (dark bg) | 'secondary' (light bg)
    """
    if style == "secondary":
        return ctk.CTkButton(
            parent,
            text=text,
            command=command,
            corner_radius=2,
            fg_color="#E5E7EB",
            hover_color="#D1D5DB",
            text_color="#1F2937",
            font=("Segoe UI", 12, "bold"),
            height=30,
        )
    return ctk.CTkButton(
        parent,
        text=text,
        command=command,
        corner_radius=2,
        fg_color="#1F2937",
        hover_color="#111827",
        text_color="#FFFFFF",
        font=("Segoe UI", 12, "bold"),
        height=30,
    )


def make_status_bar(parent) -> ctk.CTkLabel:
    """Bottom status bar label."""
    return ctk.CTkLabel(
        parent,
        text="Ready — Load a file to begin.",
        font=("Segoe UI", 11),
        text_color="#6B7280",
        anchor="w",
    )
