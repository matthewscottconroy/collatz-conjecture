"""Shared Catppuccin Mocha colour palette and matplotlib style helper.

Importing from here keeps colour definitions DRY across all GUI modules.
"""
from __future__ import annotations

# ── Background ─────────────────────────────────────────────────────────────
BG_DARK   = "#1e1e2e"
BG_PANEL  = "#2a2a3e"
BG_INPUT  = "#313145"

# ── Text / chrome ──────────────────────────────────────────────────────────
FG_TEXT    = "#cdd6f4"
FG_ACCENT  = "#89b4fa"   # Catppuccin Blue
FG_MUTED   = "#6c7086"
BTN_BG     = "#45475a"
BTN_ACTIVE = "#585b70"
HIGHLIGHT  = "#a6e3a1"   # Catppuccin Green

# ── Named data colours ─────────────────────────────────────────────────────
COL_PATH  = "#f9e2af"   # Catppuccin Yellow  — path / "warm" accent
COL_ODD   = "#f38ba8"   # Catppuccin Red     — odd Collatz steps
COL_EVEN  = "#89b4fa"   # (= FG_ACCENT)      — even Collatz steps


def style_axes(ax) -> None:  # type: ignore[no-untyped-def]
    """Apply the dark-mode colour scheme to a matplotlib Axes."""
    ax.set_facecolor(BG_PANEL)
    ax.tick_params(colors=FG_MUTED, labelsize=8)
    ax.xaxis.label.set_color(FG_TEXT)
    ax.yaxis.label.set_color(FG_TEXT)
    ax.title.set_color(FG_TEXT)
    for spine in ax.spines.values():
        spine.set_edgecolor(BTN_BG)
    ax.figure.patch.set_facecolor(BG_DARK)


def style_figure(fig) -> None:  # type: ignore[no-untyped-def]
    """Apply the dark-mode theme to every axes in fig, including colorbar axes."""
    fig.patch.set_facecolor(BG_DARK)
    for ax in fig.axes:
        style_axes(ax)
