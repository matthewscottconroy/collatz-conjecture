"""Parity & Rhythm tab for the Collatz Explorer.

Shows three complementary views of a single trajectory's structure:

  ① Parity raster     — horizontal strip: blue = even step (÷2),
                         red = odd step (×3+1).  Dashed line = glide boundary.
  ② Bit-length walk   — floor(log₂ value)+1 vs step, showing the ±1.585/−1
                         random-walk interpretation and annotating the drift.
  ③ Odd-step gaps     — histogram of gaps between consecutive ×3+1 steps,
                         revealing the rhythmic "doubling-run" structure.
"""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure

from collatz.visualization import (
    plot_parity_raster,
    plot_bit_length_walk,
    plot_odd_step_gaps,
)
from gui.theme import BG_DARK, BG_PANEL, BTN_BG, FG_MUTED, FG_TEXT, style_axes, style_figure


class ParityTab(ttk.Frame):
    """Notebook tab with three single-sequence parity/rhythm plots."""

    def __init__(self, parent: ttk.Notebook) -> None:
        super().__init__(parent)
        self.fig = Figure(facecolor=BG_DARK)
        gs = self.fig.add_gridspec(3, 1, height_ratios=[1, 3, 3], hspace=0.65)
        self.ax_parity = self.fig.add_subplot(gs[0], facecolor=BG_PANEL)
        self.ax_bits   = self.fig.add_subplot(gs[1], facecolor=BG_PANEL)
        self.ax_gaps   = self.fig.add_subplot(gs[2], facecolor=BG_PANEL)

        for ax in (self.ax_parity, self.ax_bits, self.ax_gaps):
            style_axes(ax)

        self.canvas = FigureCanvasTkAgg(self.fig, master=self)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        tb_frame = ttk.Frame(self)
        tb_frame.pack(fill=tk.X)
        toolbar = NavigationToolbar2Tk(self.canvas, tb_frame)
        toolbar.config(bg=BG_PANEL)
        toolbar.update()

    def build(self, n: int, seq: list[int]) -> None:
        """Rebuild all three subplots for the given starting value."""
        self.fig.clf()
        gs = self.fig.add_gridspec(3, 1, height_ratios=[1, 3, 3], hspace=0.65)
        self.ax_parity = self.fig.add_subplot(gs[0], facecolor=BG_PANEL)
        self.ax_bits   = self.fig.add_subplot(gs[1], facecolor=BG_PANEL)
        self.ax_gaps   = self.fig.add_subplot(gs[2], facecolor=BG_PANEL)

        for ax in (self.ax_parity, self.ax_bits, self.ax_gaps):
            style_axes(ax)

        plot_parity_raster(self.ax_parity, n, seq=seq)
        plot_bit_length_walk(self.ax_bits, n, seq=seq)
        plot_odd_step_gaps(self.ax_gaps, n, seq=seq)

        style_figure(self.fig)
        self.canvas.draw()
