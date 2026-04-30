"""
Graph tab — force-directed Collatz graph visualisation.

Shows every integer in [1, n] (up to MAX_NODES) as a node, with directed
edges  v → collatz_step(v)  when the successor also belongs to the graph.

Colour coding
-------------
  Chosen n           blue   (#89b4fa)
  On n's path to 1   yellow (#f9e2af)
  All other nodes    dim grey (#45475a)

Physics
-------
Spring / repulsion force-directed layout with velocity damping and a
tiny random drift, giving a slow "underwater" feel.  Runs at ~30 fps
via tk.Canvas.after().  Nodes can be dragged; the graph topology is
preserved.
"""
from __future__ import annotations

import math
import random
import tkinter as tk
from dataclasses import dataclass
from tkinter import ttk

from collatz.core import step as _cstep

# --------------------------------------------------------------------------
# Colours
# --------------------------------------------------------------------------
from gui.theme import BG_DARK as _BG, BG_PANEL as _BG_PANEL, FG_TEXT as _FG
from gui.theme import FG_ACCENT as _ACCENT, COL_PATH as _PATH, BTN_BG as _OTHER

_EDGE_HOT = "#89dceb"   # edge between highlighted nodes
_EDGE_DIM = "#585b70"   # all other edges

# --------------------------------------------------------------------------
# Node geometry
# --------------------------------------------------------------------------
_R_CHOSEN = 18
_R_PATH   = 14
_R_OTHER  = 10

# --------------------------------------------------------------------------
# Physics constants
# --------------------------------------------------------------------------
_REPULSION  = 5000.0   # pairwise repulsion strength
_SPRING_K   = 0.035    # spring constant along edges
_REST_LEN   = 85.0     # natural spring length (pixels)
_DAMPING    = 0.82     # velocity damping per tick  (lower = floatier)
_GRAVITY    = 0.007    # pull toward canvas centre
_DRIFT      = 0.25     # random drift amplitude per tick

MAX_NODES = 300        # upper cap before we fall back to path-only mode


# --------------------------------------------------------------------------
# Data
# --------------------------------------------------------------------------

@dataclass
class _Node:
    value:    int
    fill:     str
    radius:   int
    x:        float = 0.0
    y:        float = 0.0
    vx:       float = 0.0
    vy:       float = 0.0
    dragging: bool  = False
    oval_id:  int   = -1
    text_id:  int   = -1


# --------------------------------------------------------------------------
# Tab widget
# --------------------------------------------------------------------------

class GraphTab(ttk.Frame):
    """Notebook tab with a live force-directed Collatz graph."""

    def __init__(self, parent: ttk.Notebook) -> None:
        super().__init__(parent)
        self._nodes:      list[_Node]           = []
        self._edges:      list[tuple[int, int]] = []   # (src_idx, dst_idx)
        self._edge_ids:   list[int]             = []    # canvas item IDs
        self._running:    bool                  = False
        self._after_id:   str | None            = None  # pending after() callback
        self._tick_ms:    int                   = 33
        self._drag_node:  _Node | None          = None
        self._drag_ox:    float                 = 0.0
        self._drag_oy:    float                 = 0.0
        self._pan_start:  tuple[float, float] | None        = None
        self._pan_base:   list[tuple[float, float]]         = []
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

        # Legend row
        legend = tk.Frame(self, bg=_BG)
        legend.pack(fill=tk.X, padx=8, pady=(2, 0))
        for colour, label in ((_ACCENT, "chosen n"), (_PATH, "n's path"), (_OTHER, "other")):
            dot = tk.Canvas(legend, width=12, height=12, bg=_BG, highlightthickness=0)
            dot.create_oval(1, 1, 11, 11, fill=colour, outline="")
            dot.pack(side=tk.LEFT, padx=(0, 2))
            tk.Label(legend, text=label, bg=_BG, fg=_FG,
                     font=("TkDefaultFont", 7)).pack(side=tk.LEFT, padx=(0, 10))

        self._canvas = tk.Canvas(self, bg=_BG, highlightthickness=0)
        self._canvas.pack(fill=tk.BOTH, expand=True)
        self._canvas.bind("<ButtonPress-1>",   self._on_press)
        self._canvas.bind("<B1-Motion>",       self._on_drag)
        self._canvas.bind("<ButtonRelease-1>", self._on_release)
        # Scroll-wheel zoom (Linux Button-4/5; Windows/macOS MouseWheel)
        self._canvas.bind("<MouseWheel>", self._on_scroll)
        self._canvas.bind("<Button-4>",   self._on_scroll)
        self._canvas.bind("<Button-5>",   self._on_scroll)
        # Middle-button pan
        self._canvas.bind("<ButtonPress-2>",  self._on_pan_start)
        self._canvas.bind("<B2-Motion>",      self._on_pan)

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def build_graph(self, n: int, seq: list[int]) -> None:
        """Rebuild and animate the Collatz graph for starting value *n*."""
        self._stop()
        self._canvas.delete("all")
        self._nodes    = []
        self._edges    = []
        self._edge_ids = []

        path_set = set(seq)

        if n <= MAX_NODES:
            node_values = list(range(1, n + 1))
            self._info_var.set(
                f"n = {n:,} — {len(node_values)} nodes.  "
                "Drag any node to rearrange."
            )
        else:
            # Too many nodes for a comfortable layout; show only path values.
            node_values = sorted(path_set)
            self._info_var.set(
                f"n = {n:,} is large — showing the {len(node_values)} nodes "
                f"on its path to 1  (cap: {MAX_NODES})."
            )

        # Build node list
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

        # Build edge list: v → collatz_step(v)  (if successor is in our set)
        for i, node in enumerate(self._nodes):
            if node.value == 1:
                continue
            succ = _cstep(node.value)
            if succ in val_to_idx:
                self._edges.append((i, val_to_idx[succ]))

        # Slower tick for denser graphs
        self._tick_ms = 33 if n <= 100 else (50 if n <= 200 else 66)

        self._init_positions()
        self._draw_all()
        self._start()

    # ------------------------------------------------------------------
    # Initialisation
    # ------------------------------------------------------------------

    def _init_positions(self) -> None:
        self._canvas.update_idletasks()
        w = max(self._canvas.winfo_width(), 500)
        h = max(self._canvas.winfo_height(), 400)
        cx, cy = w / 2, h / 2
        nn = len(self._nodes)
        if nn == 0:
            return
        radius = min(w, h) * 0.38
        for i, node in enumerate(self._nodes):
            angle = 2 * math.pi * i / nn
            node.x = cx + radius * math.cos(angle)
            node.y = cy + radius * math.sin(angle)

    # ------------------------------------------------------------------
    # Canvas drawing
    # ------------------------------------------------------------------

    def _draw_all(self) -> None:
        canvas = self._canvas
        canvas.delete("all")
        self._edge_ids = []

        # Edges (drawn first, so nodes sit on top)
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

        # Nodes
        for node in self._nodes:
            r = node.radius
            oid = canvas.create_oval(
                node.x - r, node.y - r, node.x + r, node.y + r,
                fill=node.fill, outline=_BG, width=2, tags="node",
            )
            # Dark text on light nodes, light text on dark nodes
            fg = _BG if node.fill in (_ACCENT, _PATH) else _FG
            fs = 7 if node.value > 99 else (8 if node.value > 9 else 9)
            tid = canvas.create_text(
                node.x, node.y,
                text=str(node.value),
                fill=fg, font=("TkDefaultFont", fs, "bold"),
                tags="label",
            )
            node.oval_id = oid
            node.text_id = tid

    def _update_canvas(self) -> None:
        canvas = self._canvas
        for idx, (src_i, dst_i) in enumerate(self._edges):
            src = self._nodes[src_i]
            dst = self._nodes[dst_i]
            x1, y1, x2, y2 = self._edge_endpoints(src, dst)
            canvas.coords(self._edge_ids[idx], x1, y1, x2, y2)
        for node in self._nodes:
            r = node.radius
            canvas.coords(node.oval_id,
                          node.x - r, node.y - r, node.x + r, node.y + r)
            canvas.coords(node.text_id, node.x, node.y)

    @staticmethod
    def _edge_endpoints(src: _Node, dst: _Node) -> tuple[float, float, float, float]:
        """Return (x1,y1,x2,y2) at the node circumferences, not centres."""
        dx = dst.x - src.x
        dy = dst.y - src.y
        d = math.sqrt(dx * dx + dy * dy) + 0.001
        x1 = src.x + dx * src.radius / d
        y1 = src.y + dy * src.radius / d
        x2 = dst.x - dx * dst.radius / d
        y2 = dst.y - dy * dst.radius / d
        return x1, y1, x2, y2

    # ------------------------------------------------------------------
    # Physics loop
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

        nodes = self._nodes
        nn = len(nodes)
        w = self._canvas.winfo_width() or 500
        h = self._canvas.winfo_height() or 400
        cx, cy = w / 2, h / 2

        xs = [nd.x for nd in nodes]
        ys = [nd.y for nd in nodes]
        fx = [0.0] * nn
        fy = [0.0] * nn

        # Pairwise repulsion
        for i in range(nn):
            for j in range(i + 1, nn):
                ddx = xs[i] - xs[j]
                ddy = ys[i] - ys[j]
                d2  = ddx * ddx + ddy * ddy + 1.0
                d   = math.sqrt(d2)
                f   = _REPULSION / d2
                ffx = f * ddx / d
                ffy = f * ddy / d
                fx[i] += ffx;  fy[i] += ffy
                fx[j] -= ffx;  fy[j] -= ffy

        # Spring attraction along edges
        for si, di in self._edges:
            ddx = xs[di] - xs[si]
            ddy = ys[di] - ys[si]
            d   = math.sqrt(ddx * ddx + ddy * ddy) + 0.001
            f   = _SPRING_K * (d - _REST_LEN)
            ffx = f * ddx / d
            ffy = f * ddy / d
            fx[si] += ffx;  fy[si] += ffy
            fx[di] -= ffx;  fy[di] -= ffy

        # Per-node: gravity + drift + integrate
        for i, node in enumerate(nodes):
            if node.dragging:
                continue
            fx[i] += _GRAVITY * (cx - xs[i])
            fy[i] += _GRAVITY * (cy - ys[i])
            fx[i] += random.uniform(-_DRIFT, _DRIFT)
            fy[i] += random.uniform(-_DRIFT, _DRIFT)
            node.vx = (node.vx + fx[i]) * _DAMPING
            node.vy = (node.vy + fy[i]) * _DAMPING
            node.x  += node.vx
            node.y  += node.vy

        self._update_canvas()
        self._after_id = self._canvas.after(self._tick_ms, self._tick)

    # ------------------------------------------------------------------
    # Mouse / drag
    # ------------------------------------------------------------------

    def _on_press(self, event: tk.Event) -> None:  # type: ignore[type-arg]
        best: _Node | None = None
        best_d2 = float("inf")
        for node in self._nodes:
            dx = event.x - node.x
            dy = event.y - node.y
            d2 = dx * dx + dy * dy
            hit = (node.radius + 6) ** 2
            if d2 < hit and d2 < best_d2:
                best, best_d2 = node, d2
        if best is not None:
            self._drag_node = best
            best.dragging  = True
            self._drag_ox  = event.x - best.x
            self._drag_oy  = event.y - best.y

    def _on_drag(self, event: tk.Event) -> None:  # type: ignore[type-arg]
        if self._drag_node is not None:
            self._drag_node.x = event.x - self._drag_ox
            self._drag_node.y = event.y - self._drag_oy

    def _on_release(self, _event: tk.Event) -> None:  # type: ignore[type-arg]
        if self._drag_node is not None:
            self._drag_node.vx = 0.0
            self._drag_node.vy = 0.0
            self._drag_node.dragging = False
            self._drag_node = None

    def _on_scroll(self, event: tk.Event) -> None:  # type: ignore[type-arg]
        """Zoom in/out centred on the cursor position."""
        if not self._nodes:
            return
        zoom_in = event.num == 4 or (hasattr(event, "delta") and event.delta > 0)
        factor = 1.1 if zoom_in else (1.0 / 1.1)
        cx, cy = float(event.x), float(event.y)
        for node in self._nodes:
            node.x = cx + (node.x - cx) * factor
            node.y = cy + (node.y - cy) * factor

    def _on_pan_start(self, event: tk.Event) -> None:  # type: ignore[type-arg]
        """Record starting position for a middle-button pan gesture."""
        self._pan_start = (float(event.x), float(event.y))
        self._pan_base  = [(n.x, n.y) for n in self._nodes]

    def _on_pan(self, event: tk.Event) -> None:  # type: ignore[type-arg]
        """Translate all nodes by the middle-button drag offset."""
        if self._pan_start is None or not self._nodes:
            return
        dx = event.x - self._pan_start[0]
        dy = event.y - self._pan_start[1]
        for node, (bx, by) in zip(self._nodes, self._pan_base):
            node.x = bx + dx
            node.y = by + dy
