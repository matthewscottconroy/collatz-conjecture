"""
Graph tab — hierarchical Collatz graph visualisation.

Node set
--------
For n ≤ MAX_N we show every integer in [1, n] **plus** every value that
appears in n's Collatz path to 1 (some path values exceed n and were
previously invisible, making the chosen node appear disconnected).

Edges
-----
For each visible node v we follow Collatz steps until we land on another
visible node and draw the (possibly compressed) edge there.  This ensures
every node has an outgoing edge and the graph is fully connected.

Layout
------
Nodes are placed in horizontal layers by stopping time.  Up to MAX_LEVELS
distinct y-bands are used; when there are more unique stopping times than
MAX_LEVELS the times are binned so no band is thinner than ~1 node radius.
Within each band the x-spreading physics runs until velocities settle.

Colour coding
-------------
  Chosen n           blue   (#89b4fa)
  On n's path to 1   yellow (#f9e2af)
  All other nodes    dim grey (#45475a)
"""
from __future__ import annotations

import math
import random
from collections import defaultdict
from dataclasses import dataclass
from tkinter import ttk
import tkinter as tk

from collatz.core import step as _cstep, total_stopping_time as _tst

from gui.theme import BG_DARK as _BG, FG_TEXT as _FG
from gui.theme import FG_ACCENT as _ACCENT, COL_PATH as _PATH, BTN_BG as _OTHER

_EDGE_HOT = "#89dceb"
_EDGE_DIM  = "#585b70"

_R_CHOSEN = 16
_R_PATH   = 12
_R_OTHER  = 9

# Maximum integer range shown alongside the path.
MAX_N = 150

# Maximum number of distinct y-bands in the layout.
# When unique stopping times exceed this, they are binned.
MAX_LEVELS = 28

# Physics — x-axis spreading only; y is anchored to each band.
_X_REPULSION = 3500.0
_X_SPRING_K  = 0.03
_X_REST_LEN  = 60.0
_X_CENTER_K  = 0.012
_Y_ANCHOR_K  = 0.40
_DAMPING     = 0.68
_SETTLE_VEL  = 0.35
_MAX_TICKS   = 600

# y-proximity threshold: only repel nodes whose bands are close in y.
_LAYER_Y_THRESH = 85.0

# Steps to follow when searching for the next visible node.
_MAX_FOLLOW  = 2_000_000


@dataclass
class _Node:
    value:    int
    fill:     str
    radius:   int
    x:        float = 0.0
    y:        float = 0.0
    target_y: float = 0.0
    vx:       float = 0.0
    vy:       float = 0.0
    dragging: bool  = False
    oval_id:  int   = -1
    text_id:  int   = -1


class GraphTab(ttk.Frame):
    """Notebook tab with a hierarchical, self-settling Collatz graph."""

    def __init__(self, parent: ttk.Notebook) -> None:
        super().__init__(parent)
        self._nodes:      list[_Node]                      = []
        self._edges:      list[tuple[int, int]]            = []
        self._edge_ids:   list[int]                        = []
        self._running:    bool                             = False
        self._after_id:   str | None                       = None
        self._tick_ms:    int                              = 33
        self._tick_count: int                              = 0
        self._drag_node:  _Node | None                     = None
        self._drag_ox:    float                            = 0.0
        self._drag_oy:    float                            = 0.0
        self._pan_start:  tuple[float, float] | None       = None
        self._pan_base:   list[tuple[float, float, float]] = []
        self._build()

    # ------------------------------------------------------------------
    # Layout
    # ------------------------------------------------------------------

    def _build(self) -> None:
        self._info_var = tk.StringVar(value="Explore a number to see its graph.")
        tk.Label(
            self, textvariable=self._info_var,
            bg=_BG, fg=_FG, font=("TkDefaultFont", 8), anchor="w", padx=8,
        ).pack(fill=tk.X, pady=(4, 0))

        legend = tk.Frame(self, bg=_BG)
        legend.pack(fill=tk.X, padx=8, pady=(2, 0))
        for colour, label in ((_ACCENT, "chosen n"), (_PATH, "n's path"), (_OTHER, "other")):
            dot = tk.Canvas(legend, width=12, height=12, bg=_BG, highlightthickness=0)
            dot.create_oval(1, 1, 11, 11, fill=colour, outline="")
            dot.pack(side=tk.LEFT, padx=(0, 2))
            tk.Label(legend, text=label, bg=_BG, fg=_FG,
                     font=("TkDefaultFont", 7)).pack(side=tk.LEFT, padx=(0, 10))

        tk.Label(
            legend,
            text="scroll=zoom  middle-drag=pan  left-drag=move node",
            bg=_BG, fg="#6c7086", font=("TkDefaultFont", 7),
        ).pack(side=tk.RIGHT, padx=8)

        self._canvas = tk.Canvas(self, bg=_BG, highlightthickness=0)
        self._canvas.pack(fill=tk.BOTH, expand=True)
        self._canvas.bind("<ButtonPress-1>",   self._on_press)
        self._canvas.bind("<B1-Motion>",       self._on_drag)
        self._canvas.bind("<ButtonRelease-1>", self._on_release)
        self._canvas.bind("<MouseWheel>", self._on_scroll)
        self._canvas.bind("<Button-4>",   self._on_scroll)
        self._canvas.bind("<Button-5>",   self._on_scroll)
        self._canvas.bind("<ButtonPress-2>",  self._on_pan_start)
        self._canvas.bind("<B2-Motion>",      self._on_pan)

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def build_graph(self, n: int, seq: list[int]) -> None:
        """Rebuild and display the Collatz graph for starting value *n*."""
        self._stop()
        self._canvas.delete("all")
        self._nodes      = []
        self._edges      = []
        self._edge_ids   = []
        self._tick_count = 0

        path_set = set(seq)

        if n <= MAX_N:
            # Show every integer in [1, n] PLUS every value on n's path to 1.
            # Path values that exceed n are included so the chosen node and
            # every step of its journey are always visible and connected.
            node_set    = set(range(1, n + 1)) | path_set
            node_values = sorted(node_set)
            n_integers  = n
            n_extra     = len(node_values) - n_integers
            if n_extra:
                self._info_var.set(
                    f"n = {n:,} — integers 1–{n} + {n_extra} path node(s) above n  "
                    f"({len(node_values)} total).  Layered by stopping time."
                )
            else:
                self._info_var.set(
                    f"n = {n:,} — {len(node_values)} nodes.  "
                    "Layered by stopping time."
                )
        else:
            # n is large: show only the Collatz path from n to 1.
            node_values = sorted(path_set)
            self._info_var.set(
                f"n = {n:,} is large — showing the {len(node_values)} "
                f"nodes on its path to 1."
            )

        val_to_idx: dict[int, int] = {}
        for i, v in enumerate(node_values):
            if v == n:
                fill, radius = _ACCENT, _R_CHOSEN
            elif v in path_set:
                fill, radius = _PATH, _R_PATH
            else:
                fill, radius = _OTHER, _R_OTHER
            self._nodes.append(_Node(value=v, fill=fill, radius=radius))
            val_to_idx[v] = i

        # Build edges: follow Collatz steps from each node until we land on
        # another visible node.  This guarantees full connectivity even when
        # the immediate successor is outside the visible set.
        val_set = set(val_to_idx)
        for i, node in enumerate(self._nodes):
            if node.value == 1:
                continue
            current = node.value
            for _ in range(_MAX_FOLLOW):
                current = _cstep(current)
                if current in val_set:
                    self._edges.append((i, val_to_idx[current]))
                    break

        self._init_positions()
        self._draw_all()
        self._start()

    # ------------------------------------------------------------------
    # Position initialisation — hierarchical by stopping time
    # ------------------------------------------------------------------

    def _init_positions(self) -> None:
        self._canvas.update_idletasks()
        w = max(self._canvas.winfo_width(), 500)
        h = max(self._canvas.winfo_height(), 400)

        # Stopping time = number of Collatz steps from the node to 1.
        try:
            stop_times = {nd.value: _tst(nd.value) for nd in self._nodes}
        except Exception:
            stop_times = {nd.value: i for i, nd in enumerate(self._nodes)}

        # Bin distinct stopping times into at most MAX_LEVELS y-bands so
        # that nodes are never packed into sub-pixel rows.
        distinct_sorted = sorted(set(stop_times.values()))
        n_distinct = len(distinct_sorted)

        if n_distinct <= MAX_LEVELS:
            time_to_band = {t: rank for rank, t in enumerate(distinct_sorted)}
            n_bands = n_distinct
        else:
            # Map each distinct time to one of MAX_LEVELS evenly-sized bins.
            n_bands = MAX_LEVELS
            time_to_band = {
                t: min(int(rank * n_bands / n_distinct), n_bands - 1)
                for rank, t in enumerate(distinct_sorted)
            }

        # Group nodes into bands.
        band_groups: dict[int, list[_Node]] = defaultdict(list)
        for nd in self._nodes:
            band_groups[time_to_band[stop_times[nd.value]]].append(nd)

        pad_x = 55
        pad_y = 50

        for band, band_nodes in band_groups.items():
            # band 0 (node 1, lowest stopping time) → bottom of canvas.
            frac = band / max(n_bands - 1, 1)
            y = h - pad_y - (h - 2 * pad_y) * frac

            n_at = len(band_nodes)
            for i, nd in enumerate(band_nodes):
                x = (
                    pad_x + (w - 2 * pad_x) * i / (n_at - 1)
                    if n_at > 1
                    else w / 2
                )
                nd.x        = x + random.uniform(-1.5, 1.5)
                nd.y        = y
                nd.target_y = y

    # ------------------------------------------------------------------
    # Canvas drawing
    # ------------------------------------------------------------------

    def _draw_all(self) -> None:
        canvas = self._canvas
        canvas.delete("all")
        self._edge_ids = []

        hot = {_ACCENT, _PATH}
        for src_i, dst_i in self._edges:
            src = self._nodes[src_i]
            dst = self._nodes[dst_i]
            colour = _EDGE_HOT if src.fill in hot and dst.fill in hot else _EDGE_DIM
            x1, y1, x2, y2 = self._edge_endpoints(src, dst)
            eid = canvas.create_line(
                x1, y1, x2, y2,
                fill=colour, width=1.5,
                arrow=tk.LAST, arrowshape=(8, 10, 4),
                tags="edge",
            )
            self._edge_ids.append(eid)

        for nd in self._nodes:
            r = nd.radius
            oid = canvas.create_oval(
                nd.x - r, nd.y - r, nd.x + r, nd.y + r,
                fill=nd.fill, outline=_BG, width=2, tags="node",
            )
            fg = _BG if nd.fill in (_ACCENT, _PATH) else _FG
            fs = 7 if nd.value > 99 else (8 if nd.value > 9 else 9)
            tid = canvas.create_text(
                nd.x, nd.y,
                text=str(nd.value),
                fill=fg, font=("TkDefaultFont", fs, "bold"),
                tags="label",
            )
            nd.oval_id = oid
            nd.text_id = tid

    def _update_canvas(self) -> None:
        canvas = self._canvas
        for idx, (src_i, dst_i) in enumerate(self._edges):
            src = self._nodes[src_i]
            dst = self._nodes[dst_i]
            x1, y1, x2, y2 = self._edge_endpoints(src, dst)
            canvas.coords(self._edge_ids[idx], x1, y1, x2, y2)
        for nd in self._nodes:
            r = nd.radius
            canvas.coords(nd.oval_id, nd.x - r, nd.y - r, nd.x + r, nd.y + r)
            canvas.coords(nd.text_id, nd.x, nd.y)

    @staticmethod
    def _edge_endpoints(src: _Node, dst: _Node) -> tuple[float, float, float, float]:
        dx = dst.x - src.x
        dy = dst.y - src.y
        d  = math.sqrt(dx * dx + dy * dy) + 0.001
        return (
            src.x + dx * src.radius / d,
            src.y + dy * src.radius / d,
            dst.x - dx * dst.radius / d,
            dst.y - dy * dst.radius / d,
        )

    # ------------------------------------------------------------------
    # Physics loop — runs until settled, then stops
    # ------------------------------------------------------------------

    def _start(self) -> None:
        self._running = True
        self._after_id = self._canvas.after(self._tick_ms, self._tick)

    def _stop(self) -> None:
        self._running = False
        if self._after_id is not None:
            self._canvas.after_cancel(self._after_id)
            self._after_id = None

    def _tick(self) -> None:
        self._after_id = None
        if not self._running or not self._nodes:
            return

        self._tick_count += 1
        nodes = self._nodes
        nn    = len(nodes)
        w     = self._canvas.winfo_width() or 500
        cx    = w / 2.0

        xs = [nd.x for nd in nodes]
        ys = [nd.y for nd in nodes]
        fx = [0.0] * nn
        fy = [0.0] * nn

        # Pairwise x-repulsion — skip pairs whose bands are far apart in y.
        for i in range(nn):
            for j in range(i + 1, nn):
                ddy = ys[i] - ys[j]
                if abs(ddy) > _LAYER_Y_THRESH:
                    continue
                ddx = xs[i] - xs[j]
                d2  = ddx * ddx + ddy * ddy + 1.0
                d   = math.sqrt(d2)
                f   = _X_REPULSION / d2
                ffx = f * ddx / d
                fx[i] += ffx
                fx[j] -= ffx

        # x-spring along edges.
        for si, di in self._edges:
            ddx = xs[di] - xs[si]
            d   = abs(ddx) + 0.001
            f   = _X_SPRING_K * (d - _X_REST_LEN)
            ffx = f * (ddx / d)
            fx[si] += ffx
            fx[di] -= ffx

        max_speed = 0.0
        for i, nd in enumerate(nodes):
            if nd.dragging:
                continue
            fx[i] += _X_CENTER_K * (cx - xs[i])
            fy[i]  = _Y_ANCHOR_K * (nd.target_y - ys[i])

            nd.vx = (nd.vx + fx[i]) * _DAMPING
            nd.vy = (nd.vy + fy[i]) * _DAMPING
            nd.x += nd.vx
            nd.y += nd.vy

            speed = math.sqrt(nd.vx * nd.vx + nd.vy * nd.vy)
            if speed > max_speed:
                max_speed = speed

        self._update_canvas()

        if max_speed < _SETTLE_VEL or self._tick_count >= _MAX_TICKS:
            self._running = False
            return

        self._after_id = self._canvas.after(self._tick_ms, self._tick)

    # ------------------------------------------------------------------
    # Mouse — drag, zoom, pan
    # ------------------------------------------------------------------

    def _on_press(self, event: tk.Event) -> None:  # type: ignore[type-arg]
        best: _Node | None = None
        best_d2 = float("inf")
        for nd in self._nodes:
            dx = event.x - nd.x
            dy = event.y - nd.y
            d2 = dx * dx + dy * dy
            if d2 < (nd.radius + 6) ** 2 and d2 < best_d2:
                best, best_d2 = nd, d2
        if best is not None:
            self._drag_node = best
            best.dragging   = True
            self._drag_ox   = event.x - best.x
            self._drag_oy   = event.y - best.y

    def _on_drag(self, event: tk.Event) -> None:  # type: ignore[type-arg]
        if self._drag_node is not None:
            self._drag_node.x = event.x - self._drag_ox
            self._drag_node.y = event.y - self._drag_oy
            self._update_canvas()

    def _on_release(self, _event: tk.Event) -> None:  # type: ignore[type-arg]
        if self._drag_node is not None:
            self._drag_node.vx = 0.0
            self._drag_node.vy = 0.0
            self._drag_node.dragging = False
            self._drag_node = None
            if not self._running:
                self._tick_count = 0
                self._start()

    def _on_scroll(self, event: tk.Event) -> None:  # type: ignore[type-arg]
        if not self._nodes:
            return
        zoom_in = event.num == 4 or (hasattr(event, "delta") and event.delta > 0)
        factor  = 1.1 if zoom_in else (1.0 / 1.1)
        cx, cy  = float(event.x), float(event.y)
        for nd in self._nodes:
            nd.x        = cx + (nd.x        - cx) * factor
            nd.y        = cy + (nd.y        - cy) * factor
            nd.target_y = cy + (nd.target_y - cy) * factor
        self._update_canvas()

    def _on_pan_start(self, event: tk.Event) -> None:  # type: ignore[type-arg]
        self._pan_start = (float(event.x), float(event.y))
        self._pan_base  = [(nd.x, nd.y, nd.target_y) for nd in self._nodes]

    def _on_pan(self, event: tk.Event) -> None:  # type: ignore[type-arg]
        if self._pan_start is None or not self._nodes:
            return
        dx = event.x - self._pan_start[0]
        dy = event.y - self._pan_start[1]
        for nd, (bx, by, bty) in zip(self._nodes, self._pan_base):
            nd.x        = bx  + dx
            nd.y        = by  + dy
            nd.target_y = bty + dy
        self._update_canvas()
