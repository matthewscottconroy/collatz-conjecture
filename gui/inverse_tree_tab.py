"""Inverse Predecessor Tree tab for the Collatz Explorer.

For a chosen starting value n, the *inverse Collatz map* asks: which positive
integers m satisfy step(m) = n?  Expanding recursively gives a binary tree
(with occasional single-child nodes) rooted at n where every node's Collatz
sequence passes through n.

Two predecessor types are highlighted:
  • Even predecessor  2n  (always exists) — teal  (#94e2d5)
  • Odd predecessor   (n−1)/3            — peach (#fab387)
    (exists when n ≡ 1 mod 3 and (n−1)/3 is a positive odd integer)
  • Root n itself                         — blue  (#89b4fa)
  • Nodes that also appear on n's forward sequence to 1 ("near-cycle hint")
                                          — mauve (#cba6f7)

The user can adjust the expansion depth (1–10) via a spinbox and rebuild
without re-exploring a new n.
"""
from __future__ import annotations

import tkinter as tk
from collections import deque
from tkinter import ttk

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure

from collatz.core import get_predecessors
from gui.theme import BG_DARK, BG_PANEL, BTN_BG, FG_MUTED, FG_TEXT, FG_ACCENT, style_axes, style_figure

# Node fill colours
_COL_ROOT   = FG_ACCENT   # chosen n
_COL_EVEN   = "#94e2d5"   # Catppuccin Teal — even predecessor (2n)
_COL_ODD    = "#fab387"   # Catppuccin Peach — odd predecessor ((n-1)/3)
_COL_CYCLE  = "#cba6f7"   # Catppuccin Mauve — appears in n's forward path (cycle hint)

_MAX_DEPTH  = 10
_DEFAULT_DEPTH = 6


# ---------------------------------------------------------------------------
# Tree building helpers
# ---------------------------------------------------------------------------

def _build_inverse_tree(
    root: int,
    max_depth: int,
) -> tuple[dict[int, list[int]], dict[int, str]]:
    """BFS expansion of the inverse Collatz tree.

    Returns:
        children  : {parent: [child, ...]}
        node_type : {node: 'root'|'even'|'odd'}
    """
    children:  dict[int, list[int]] = {root: []}
    node_type: dict[int, str]       = {root: "root"}
    visited = {root}
    queue: deque[tuple[int, int]] = deque([(root, 0)])

    while queue:
        curr, depth = queue.popleft()
        if depth >= max_depth:
            continue
        preds = get_predecessors(curr)
        even_pred = preds[0]   # always 2*curr
        for pred in preds:
            if pred in visited:
                continue
            visited.add(pred)
            children[curr].append(pred)
            children[pred] = []
            node_type[pred] = "even" if pred == even_pred else "odd"
            queue.append((pred, depth + 1))

    return children, node_type


def _compute_positions(
    children: dict[int, list[int]],
    root: int,
) -> dict[int, tuple[float, int]]:
    """Assign (x, depth) to every node via recursive subtree centering.

    Leaves get unit width; internal nodes span the range of their children.
    Returns positions as (x_normalised_to_0_1, depth).
    """
    positions: dict[int, tuple[float, int]] = {}

    def _assign(node: int, depth: int, left: float) -> float:
        kids = children.get(node, [])
        if not kids:
            positions[node] = (left + 0.5, depth)
            return left + 1.0
        cursor = left
        for child in kids:
            cursor = _assign(child, depth + 1, cursor)
        child_xs = [positions[c][0] for c in kids]
        positions[node] = ((min(child_xs) + max(child_xs)) / 2.0, depth)
        return cursor

    _assign(root, 0, 0.0)

    # Normalise x to [0, 1]
    xs = [p[0] for p in positions.values()]
    x_min, x_range = min(xs), max(xs) - min(xs)
    if x_range == 0:
        x_range = 1.0
    return {
        node: ((x - x_min) / x_range, depth)
        for node, (x, depth) in positions.items()
    }


# ---------------------------------------------------------------------------
# Tab widget
# ---------------------------------------------------------------------------

class InverseTreeTab(ttk.Frame):
    """Notebook tab showing the inverse Collatz predecessor tree."""

    def __init__(self, parent: ttk.Notebook) -> None:
        super().__init__(parent)
        self._n:    int       = 1
        self._seq:  list[int] = [1]
        self._build_ui()

    def _build_ui(self) -> None:
        ctrl = ttk.Frame(self, style="Panel.TFrame")
        ctrl.pack(fill=tk.X, padx=6, pady=6)

        ttk.Label(ctrl, text="Depth:", style="Panel.TLabel").grid(
            row=0, column=0, padx=(0, 4))
        self._depth_var = tk.StringVar(value=str(_DEFAULT_DEPTH))
        sb = ttk.Spinbox(ctrl, from_=1, to=_MAX_DEPTH,
                         textvariable=self._depth_var, width=4)
        sb.grid(row=0, column=1, padx=(0, 8))
        ttk.Button(ctrl, text="Rebuild", command=self._draw
                   ).grid(row=0, column=2)

        # Legend
        legend = tk.Frame(ctrl, bg=BG_PANEL)
        legend.grid(row=0, column=3, padx=(20, 0))
        for colour, label in (
            (_COL_ROOT, "n (root)"),
            (_COL_EVEN, "even pred. 2k"),
            (_COL_ODD,  "odd pred. (k−1)/3"),
            (_COL_CYCLE, "also on n's path"),
        ):
            dot = tk.Canvas(legend, width=10, height=10,
                            bg=BG_PANEL, highlightthickness=0)
            dot.create_oval(1, 1, 9, 9, fill=colour, outline="")
            dot.pack(side=tk.LEFT, padx=(0, 2))
            tk.Label(legend, text=label, bg=BG_PANEL, fg=FG_TEXT,
                     font=("TkDefaultFont", 7)).pack(side=tk.LEFT, padx=(0, 10))

        self.fig = Figure(facecolor=BG_DARK)
        self.ax  = self.fig.add_subplot(111)
        style_axes(self.ax)
        self.ax.axis("off")

        self.canvas = FigureCanvasTkAgg(self.fig, master=self)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        tb_frame = ttk.Frame(self)
        tb_frame.pack(fill=tk.X)
        toolbar = NavigationToolbar2Tk(self.canvas, tb_frame)
        toolbar.config(bg=BG_PANEL)
        toolbar.update()

    def build(self, n: int, seq: list[int]) -> None:
        """Store state and redraw the tree for a new n."""
        self._n   = n
        self._seq = seq
        self._draw()

    def _draw(self) -> None:
        try:
            depth = max(1, min(_MAX_DEPTH, int(self._depth_var.get())))
        except ValueError:
            depth = _DEFAULT_DEPTH

        children, node_type = _build_inverse_tree(self._n, depth)
        positions = _compute_positions(children, self._n)
        path_set  = set(self._seq)

        # Determine colour for each node
        def _colour(node: int) -> str:
            if node == self._n:
                return _COL_ROOT
            if node in path_set:
                return _COL_CYCLE
            ntype = node_type.get(node, "even")
            return _COL_EVEN if ntype == "even" else _COL_ODD

        self.fig.clf()
        ax = self.fig.add_subplot(111)
        style_axes(ax)
        ax.axis("off")

        max_depth_actual = max(d for _, d in positions.values()) if positions else 0
        n_nodes = len(positions)
        font_size = max(5, min(8, 200 // max(n_nodes, 1)))

        # Draw edges first
        for parent, kids in children.items():
            if parent not in positions:
                continue
            px, pd = positions[parent]
            for child in kids:
                if child not in positions:
                    continue
                cx, cd = positions[child]
                ax.plot([px, cx], [-pd, -cd], color=BTN_BG,
                        linewidth=0.7, zorder=1)

        # Draw nodes
        for node, (x, d) in positions.items():
            col = _colour(node)
            ax.scatter([x], [-d], s=max(60, 300 - n_nodes),
                       c=col, zorder=5, linewidths=0)
            text_col = BG_DARK if col != BTN_BG else FG_TEXT
            ax.text(x, -d, str(node), ha="center", va="center",
                    fontsize=font_size, fontweight="bold",
                    color=text_col, zorder=6)

        ax.set_title(
            f"Inverse Predecessor Tree  —  n = {self._n:,}   "
            f"depth = {depth}   ({n_nodes} nodes)",
            color=FG_TEXT,
        )
        # Depth labels on y-axis
        ax.set_yticks([-d for d in range(max_depth_actual + 1)])
        ax.set_yticklabels([str(d) for d in range(max_depth_actual + 1)],
                           fontsize=7)
        ax.tick_params(colors=FG_MUTED, labelsize=7, left=True,
                       labelleft=True, bottom=False, labelbottom=False)
        ax.yaxis.label.set_color(FG_TEXT)
        ax.set_ylabel("Depth", fontsize=8)
        ax.spines["left"].set_visible(True)
        ax.spines["left"].set_edgecolor(BTN_BG)

        style_figure(self.fig)
        self.fig.tight_layout()
        self.canvas.draw()
