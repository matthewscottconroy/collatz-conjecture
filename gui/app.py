"""
Collatz Conjecture Explorer — GUI application.

Built with tkinter (stdlib) and matplotlib (embedded via FigureCanvasTkAgg).

Layout
------
┌─────────────────────────────────────────────────────────────────────┐
│  Collatz Conjecture Explorer                                         │
├──────────────┬──────────────────────────────────────────────────────┤
│  LEFT PANEL  │  NOTEBOOK TABS                                       │
│  • Input     │   [Trajectory] [Log] [Phase] [Parity] [Range]       │
│  • Library   │   [Compare] [Graph] [Inverse Tree]                   │
│  • Stats     │   <matplotlib canvas or tk.Canvas>                   │
│              │                                                       │
│              │  <NavigationToolbar>                                  │
└──────────────┴──────────────────────────────────────────────────────┘
│  Status bar                                                          │
└──────────────────────────────────────────────────────────────────────┘
"""

from __future__ import annotations

import queue as _queue
import threading
import tkinter as tk
from tkinter import messagebox, ttk

import matplotlib
matplotlib.use("TkAgg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure

from collatz.analysis import compute_stats, find_interesting
from collatz.core import CollatzError, sequence, total_stopping_time
from collatz.library import (
    CATEGORY_LABELS,
    by_category,
    categories,
)
from collatz.visualization import (
    plot_altitude_scatter,
    plot_convergence_heatmap,
    plot_log_phase_portrait,
    plot_log_trajectory,
    plot_multi_trajectory,
    plot_phase_portrait,
    plot_record_holders,
    plot_stopping_time_bar,
    plot_trajectory,
    plot_trajectory_fingerprint,
)
from gui.graph_tab import GraphTab
from gui.parity_tab import ParityTab
from gui.inverse_tree_tab import InverseTreeTab
from gui.theme import (
    BG_DARK, BG_PANEL, BG_INPUT,
    FG_TEXT, FG_ACCENT, FG_MUTED,
    BTN_BG, BTN_ACTIVE, HIGHLIGHT,
    style_axes as _style_axes,
    style_figure as _style_figure,
)


class CollatzApp(tk.Tk):
    """Root application window.

    Attributes:
        _current_n  : Last successfully explored starting value.
        _current_seq: Cached sequence for _current_n (avoids recomputation).
        _compare_ns : List of n values queued for the comparison tab.
    """

    def __init__(self) -> None:
        super().__init__()
        self.title("Collatz Conjecture Explorer")
        self.geometry("1200x720")
        self.minsize(900, 600)
        self.configure(bg=BG_DARK)

        self._current_n: int = 27
        self._current_seq: list[int] = []
        self._compare_ns: list[int] = []

        self._apply_theme()
        self._build_ui()
        self._bind_shortcuts()
        self._load_library_tree()
        self._explore(self._current_n)

    # ------------------------------------------------------------------
    # Theme
    # ------------------------------------------------------------------

    def _apply_theme(self) -> None:
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure(".", background=BG_DARK, foreground=FG_TEXT,
                        fieldbackground=BG_INPUT, bordercolor=BG_PANEL,
                        troughcolor=BG_PANEL, selectbackground=FG_ACCENT,
                        selectforeground=BG_DARK)
        style.configure("TFrame", background=BG_DARK)
        style.configure("Panel.TFrame", background=BG_PANEL)
        style.configure("TLabel", background=BG_DARK, foreground=FG_TEXT)
        style.configure("Panel.TLabel", background=BG_PANEL, foreground=FG_TEXT)
        style.configure("TButton", background=BTN_BG, foreground=FG_TEXT,
                        relief="flat", padding=(6, 3))
        style.map("TButton",
                  background=[("active", BTN_ACTIVE), ("pressed", BG_INPUT)])
        style.configure("Accent.TButton", background=FG_ACCENT,
                        foreground=BG_DARK, font=("TkDefaultFont", 9, "bold"))
        style.map("Accent.TButton",
                  background=[("active", HIGHLIGHT), ("pressed", HIGHLIGHT)])
        style.configure("TNotebook", background=BG_DARK, borderwidth=0)
        style.configure("TNotebook.Tab", background=BTN_BG, foreground=FG_TEXT,
                        padding=(10, 4))
        style.map("TNotebook.Tab",
                  background=[("selected", BG_PANEL)],
                  foreground=[("selected", FG_ACCENT)])
        style.configure("Treeview", background=BG_INPUT, foreground=FG_TEXT,
                        fieldbackground=BG_INPUT, rowheight=22)
        style.configure("Treeview.Heading", background=BG_PANEL,
                        foreground=FG_ACCENT)
        style.map("Treeview",
                  background=[("selected", FG_ACCENT)],
                  foreground=[("selected", BG_DARK)])
        style.configure("TEntry", fieldbackground=BG_INPUT, foreground=FG_TEXT,
                        insertcolor=FG_TEXT)
        style.configure("TScrollbar", background=BTN_BG, troughcolor=BG_PANEL)

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        self._build_menu()

        paned = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

        left = ttk.Frame(paned, style="Panel.TFrame", width=260)
        left.pack_propagate(False)
        paned.add(left, weight=0)

        right = ttk.Frame(paned)
        paned.add(right, weight=1)

        self._build_left_panel(left)
        self._build_right_panel(right)
        self._build_status_bar()

    def _build_menu(self) -> None:
        menubar = tk.Menu(self, bg=BG_PANEL, fg=FG_TEXT, tearoff=False,
                          activebackground=FG_ACCENT, activeforeground=BG_DARK)
        self.config(menu=menubar)

        file_menu = tk.Menu(menubar, tearoff=False, bg=BG_PANEL, fg=FG_TEXT,
                            activebackground=FG_ACCENT, activeforeground=BG_DARK)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Export current plot…",
                              command=self._export_plot)
        file_menu.add_separator()
        file_menu.add_command(label="Quit", command=self.destroy)

        help_menu = tk.Menu(menubar, tearoff=False, bg=BG_PANEL, fg=FG_TEXT,
                            activebackground=FG_ACCENT, activeforeground=BG_DARK)
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="About…", command=self._show_about)

    def _build_left_panel(self, parent: ttk.Frame) -> None:
        parent.columnconfigure(0, weight=1)

        # ── Input section ────────────────────────────────────────────
        input_frame = ttk.LabelFrame(parent, text="Explore",
                                     style="Panel.TFrame", padding=6)
        input_frame.grid(row=0, column=0, sticky="ew", padx=6, pady=(6, 3))
        input_frame.columnconfigure(0, weight=1)

        ttk.Label(input_frame, text="Starting value n:", style="Panel.TLabel"
                  ).grid(row=0, column=0, columnspan=2, sticky="w")

        self._n_var = tk.StringVar(value=str(self._current_n))
        entry = ttk.Entry(input_frame, textvariable=self._n_var, width=14)
        entry.grid(row=1, column=0, sticky="ew", padx=(0, 4))
        entry.bind("<Return>", lambda _: self._on_explore())

        ttk.Button(input_frame, text="Explore", style="Accent.TButton",
                   command=self._on_explore
                   ).grid(row=1, column=1)

        ttk.Button(input_frame, text="+ Compare",
                   command=self._add_to_compare
                   ).grid(row=2, column=0, columnspan=2, sticky="ew", pady=(4, 0))

        # ── Library section ──────────────────────────────────────────
        lib_frame = ttk.LabelFrame(parent, text="Library",
                                   style="Panel.TFrame", padding=6)
        lib_frame.grid(row=1, column=0, sticky="nsew", padx=6, pady=3)
        lib_frame.columnconfigure(0, weight=1)
        lib_frame.rowconfigure(0, weight=1)
        parent.rowconfigure(1, weight=1)

        self._lib_tree = ttk.Treeview(lib_frame, show="tree", selectmode="browse")
        self._lib_tree.column("#0", width=220, stretch=True)
        vsb = ttk.Scrollbar(lib_frame, orient="vertical",
                            command=self._lib_tree.yview)
        self._lib_tree.configure(yscrollcommand=vsb.set)
        self._lib_tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        self._lib_tree.bind("<<TreeviewSelect>>", self._on_library_select)
        self._lib_tree.bind("<Double-1>", self._on_library_double_click)

        ttk.Button(lib_frame, text="Load selected",
                   command=self._on_load_library_entry
                   ).grid(row=1, column=0, columnspan=2, sticky="ew", pady=(4, 0))

        # ── Stats section ────────────────────────────────────────────
        stats_frame = ttk.LabelFrame(parent, text="Statistics",
                                     style="Panel.TFrame", padding=6)
        stats_frame.grid(row=2, column=0, sticky="ew", padx=6, pady=(3, 6))

        self._stats_text = tk.Text(
            stats_frame,
            height=11,
            state=tk.DISABLED,
            bg=BG_INPUT,
            fg=FG_TEXT,
            font=("Courier", 8),
            relief="flat",
            wrap=tk.NONE,
        )
        self._stats_text.pack(fill=tk.BOTH)

    def _build_right_panel(self, parent: ttk.Frame) -> None:
        self._notebook = ttk.Notebook(parent)
        self._notebook.pack(fill=tk.BOTH, expand=True)

        self._trajectory_tab = _PlotTab(self._notebook)
        self._log_tab        = _PlotTab(self._notebook)
        self._phase_tab      = _PlotTab(self._notebook)
        self._parity_tab     = ParityTab(self._notebook)
        self._range_tab      = _RangeTab(self._notebook, self)
        self._compare_tab    = _CompareTab(self._notebook, self)
        self._graph_tab      = GraphTab(self._notebook)
        self._inverse_tab    = InverseTreeTab(self._notebook)

        self._notebook.add(self._trajectory_tab, text="  Trajectory  ")
        self._notebook.add(self._log_tab,        text="  Log Scale  ")
        self._notebook.add(self._phase_tab,      text="  Phase Plot  ")
        self._notebook.add(self._parity_tab,     text="  Parity  ")
        self._notebook.add(self._range_tab,      text="  Range Scan  ")
        self._notebook.add(self._compare_tab,    text="  Compare  ")
        self._notebook.add(self._graph_tab,      text="  Graph  ")
        self._notebook.add(self._inverse_tab,    text="  Inverse Tree  ")

        # Lazy rendering: map each renderable tab to its render function.
        # Only tabs that display per-n content are included; Range and Compare
        # manage their own state independently.
        self._tab_renderers = {
            self._trajectory_tab: self._render_trajectory,
            self._log_tab:        self._render_log,
            self._phase_tab:      self._render_phase,
            self._parity_tab:     self._render_parity,
            self._graph_tab:      self._render_graph,
            self._inverse_tab:    self._render_inverse,
        }
        self._dirty_tabs: set = set()
        self._notebook.bind("<<NotebookTabChanged>>", self._on_tab_changed)

    def _build_status_bar(self) -> None:
        self._status_var = tk.StringVar(value="Ready.")
        bar = tk.Label(self, textvariable=self._status_var, anchor="w",
                       bg=BG_PANEL, fg=FG_MUTED, font=("TkDefaultFont", 8),
                       padx=6)
        bar.pack(side=tk.BOTTOM, fill=tk.X)

    # ------------------------------------------------------------------
    # Library tree
    # ------------------------------------------------------------------

    def _load_library_tree(self) -> None:
        for cat in categories():
            label = CATEGORY_LABELS.get(cat, cat)
            branch = self._lib_tree.insert("", "end", iid=f"cat:{cat}",
                                           text=f"▶  {label}", open=False)
            for entry in by_category(cat):
                # Use a delimiter that cannot appear in category names.
                iid = f"entry:{entry.n}::{cat}"
                self._lib_tree.insert(
                    branch, "end", iid=iid,
                    text=f"  {entry.n:,}  —  {entry.name}",
                )

    # ------------------------------------------------------------------
    # Event handlers
    # ------------------------------------------------------------------

    def _on_explore(self) -> None:
        raw = self._n_var.get().strip().replace(",", "").replace("_", "")
        try:
            n = int(raw)
        except ValueError:
            messagebox.showerror("Invalid input",
                                 f"'{raw}' is not a valid integer.")
            return
        if n <= 0:
            messagebox.showerror("Invalid input", "n must be a positive integer.")
            return

        self._status_var.set(f"Computing sequence for n = {n:,} …")
        self.update_idletasks()

        try:
            self._explore(n)
            self._status_var.set(f"n = {n:,}  ready.")
        except CollatzError as exc:
            messagebox.showerror("Collatz Error", str(exc))
            self._status_var.set("Error.")

    def _explore(self, n: int) -> None:
        """Compute sequence once, mark all renderable tabs dirty, render the active one."""
        seq = sequence(n)
        self._current_n = n
        self._current_seq = seq
        self._update_stats(n, seq)
        self._dirty_tabs = set(self._tab_renderers.keys())
        self._render_active_tab()

    def _on_library_select(self, _event: tk.Event) -> None:  # type: ignore[type-arg]
        sel = self._lib_tree.selection()
        if not sel:
            return
        iid = sel[0]
        if iid.startswith("entry:"):
            # IID format: "entry:{n}::{cat}" — split on "::" to avoid
            # collisions if a future category name contains a single colon.
            _, rest = iid.split(":", 1)
            n_str, cat = rest.split("::", 1)
            n = int(n_str)
            self._n_var.set(str(n))
            entries = [e for e in by_category(cat) if e.n == n]
            if entries:
                self._status_var.set(entries[0].description[:120])

    def _on_library_double_click(self, _event: tk.Event) -> None:  # type: ignore[type-arg]
        """Double-clicking a library entry immediately loads and explores it."""
        sel = self._lib_tree.selection()
        if sel and sel[0].startswith("entry:"):
            self._on_explore()

    def _on_load_library_entry(self) -> None:
        sel = self._lib_tree.selection()
        if not sel:
            return
        if sel[0].startswith("entry:"):
            self._on_explore()

    def _add_to_compare(self) -> None:
        raw = self._n_var.get().strip().replace(",", "").replace("_", "")
        try:
            n = int(raw)
            if n <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Invalid input", "n must be a positive integer.")
            return
        if n in self._compare_ns:
            self._status_var.set(f"n = {n:,} is already in the comparison queue.")
            return
        self._compare_ns.append(n)
        self._compare_tab.refresh_list(self._compare_ns)
        self._notebook.select(self._compare_tab)
        self._status_var.set(
            f"Added {n:,} to comparison. {len(self._compare_ns)} sequence(s) queued."
        )

    # ------------------------------------------------------------------
    # Tab-change event and lazy rendering
    # ------------------------------------------------------------------

    def _on_tab_changed(self, _event: tk.Event) -> None:  # type: ignore[type-arg]
        self._render_active_tab()

    def _render_active_tab(self) -> None:
        """If the currently visible tab is dirty, render it now."""
        try:
            current = self._notebook.nametowidget(self._notebook.select())
        except (tk.TclError, KeyError):
            return
        renderer = self._tab_renderers.get(current)
        if renderer is not None and current in self._dirty_tabs:
            self._dirty_tabs.discard(current)
            renderer()

    # ------------------------------------------------------------------
    # Per-tab render helpers
    # ------------------------------------------------------------------

    def _render_trajectory(self) -> None:
        self._trajectory_tab.clear()
        plot_trajectory(self._trajectory_tab.ax, self._current_n,
                        seq=self._current_seq)
        self._trajectory_tab.draw()

    def _render_log(self) -> None:
        self._log_tab.clear()
        plot_log_trajectory(self._log_tab.ax, self._current_n,
                            seq=self._current_seq)
        self._log_tab.draw()

    def _render_phase(self) -> None:
        self._phase_tab.clear()
        seq = self._current_seq
        if len(seq) > 500:
            plot_log_phase_portrait(self._phase_tab.ax, self._current_n, seq=seq)
        else:
            plot_phase_portrait(self._phase_tab.ax, self._current_n, seq=seq)
        self._phase_tab.draw()

    def _render_parity(self) -> None:
        self._parity_tab.build(self._current_n, self._current_seq)

    def _render_graph(self) -> None:
        self._graph_tab.build_graph(self._current_n, self._current_seq)

    def _render_inverse(self) -> None:
        self._inverse_tab.build(self._current_n, self._current_seq)

    # ------------------------------------------------------------------
    # Keyboard shortcuts
    # ------------------------------------------------------------------

    def _bind_shortcuts(self) -> None:
        """Bind global keyboard shortcuts to the root window."""
        self.bind("<Control-Return>", lambda _: self._on_explore())
        self.bind("<Alt-Left>",       lambda _: self._step_n(-1))
        self.bind("<Alt-Right>",      lambda _: self._step_n(+1))

    def _step_n(self, delta: int) -> None:
        """Increment or decrement n by delta and explore the result."""
        raw = self._n_var.get().strip().replace(",", "").replace("_", "")
        try:
            n = int(raw)
        except ValueError:
            return
        self._n_var.set(str(max(1, n + delta)))
        self._on_explore()

    def _update_stats(self, n: int, seq: list[int]) -> None:
        stats = compute_stats(n, seq=seq)
        text = stats.summary()
        self._stats_text.config(state=tk.NORMAL)
        self._stats_text.delete("1.0", tk.END)
        self._stats_text.insert(tk.END, text)
        self._stats_text.config(state=tk.DISABLED)

    # ------------------------------------------------------------------
    # Misc
    # ------------------------------------------------------------------

    def _export_plot(self) -> None:
        from tkinter import filedialog
        tab_idx = self._notebook.index("current")
        tabs = [
            self._trajectory_tab, self._log_tab, self._phase_tab,
            self._parity_tab, self._range_tab, self._compare_tab,
            self._graph_tab, self._inverse_tab,
        ]
        tab = tabs[tab_idx]
        if not hasattr(tab, "fig"):
            messagebox.showinfo(
                "Export",
                "The Graph tab uses a live canvas — export is not available.",
            )
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[("PNG image", "*.png"), ("PDF", "*.pdf"),
                       ("SVG", "*.svg"), ("All files", "*.*")],
        )
        if path:
            tab.fig.savefig(path, dpi=150, bbox_inches="tight")
            self._status_var.set(f"Exported to {path}")

    def _show_about(self) -> None:
        messagebox.showinfo(
            "About Collatz Explorer",
            "Collatz Conjecture Explorer v1.1.0\n\n"
            "Visualise and analyse Collatz sequences.\n"
            "Find interesting trajectories, explore near-cycle behaviour,\n"
            "and browse a curated library of remarkable starting values.\n\n"
            "Built with Python · tkinter · matplotlib",
        )


# ---------------------------------------------------------------------------
# Tab widgets
# ---------------------------------------------------------------------------

class _PlotTab(ttk.Frame):
    """A notebook tab that hosts a single matplotlib Figure."""

    def __init__(self, parent: ttk.Notebook) -> None:
        super().__init__(parent)
        self.fig = Figure(figsize=(7, 5), facecolor=BG_DARK)
        self.ax = self.fig.add_subplot(111, facecolor=BG_PANEL)
        _style_axes(self.ax)

        self.canvas = FigureCanvasTkAgg(self.fig, master=self)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        toolbar_frame = ttk.Frame(self)
        toolbar_frame.pack(fill=tk.X)
        toolbar = NavigationToolbar2Tk(self.canvas, toolbar_frame)
        toolbar.config(bg=BG_PANEL)
        toolbar.update()

    def clear(self) -> None:
        self.fig.clf()
        self.ax = self.fig.add_subplot(111, facecolor=BG_PANEL)
        _style_axes(self.ax)

    def draw(self) -> None:
        _style_figure(self.fig)
        self.fig.tight_layout()
        self.canvas.draw()


# Supported range-scan plot types and their display labels.
_SCAN_PLOT_TYPES: list[tuple[str, str]] = [
    ("stopping_time",  "Stopping Time (bar)"),
    ("altitude",       "Altitude (scatter)"),
    ("heatmap_stop",   "Heatmap: Stopping Time"),
    ("heatmap_alt",    "Heatmap: Altitude"),
    ("records",        "Record Holders"),
    ("fingerprint",    "Trajectory Fingerprint"),
]
_SCAN_PLOT_VALUES = [label for _, label in _SCAN_PLOT_TYPES]
_SCAN_PLOT_KEYS   = {label: key for key, label in _SCAN_PLOT_TYPES}

# Upper cap on trajectories computed for the fingerprint plot.
_FINGERPRINT_CAP = 500


class _RangeTab(ttk.Frame):
    """Tab for scanning a range of starting values.

    Data computation runs in a background thread so the UI stays responsive.
    Matplotlib drawing happens on the main thread after the worker signals
    completion via a queue.
    """

    def __init__(self, parent: ttk.Notebook, app: CollatzApp) -> None:
        super().__init__(parent)
        self._app = app
        self._build()

    def _build(self) -> None:
        control = ttk.Frame(self, style="Panel.TFrame")
        control.pack(fill=tk.X, padx=6, pady=6)

        ttk.Label(control, text="From:", style="Panel.TLabel").grid(
            row=0, column=0, padx=(0, 4))
        self._start_var = tk.StringVar(value="1")
        ttk.Entry(control, textvariable=self._start_var, width=10).grid(
            row=0, column=1, padx=(0, 8))

        ttk.Label(control, text="To:", style="Panel.TLabel").grid(
            row=0, column=2, padx=(0, 4))
        self._end_var = tk.StringVar(value="200")
        ttk.Entry(control, textvariable=self._end_var, width=10).grid(
            row=0, column=3, padx=(0, 8))

        ttk.Label(control, text="Plot:", style="Panel.TLabel").grid(
            row=0, column=4, padx=(0, 4))
        self._plot_label = tk.StringVar(value=_SCAN_PLOT_VALUES[0])
        combo = ttk.Combobox(
            control,
            textvariable=self._plot_label,
            values=_SCAN_PLOT_VALUES,
            state="readonly",
            width=22,
        )
        combo.grid(row=0, column=5, padx=(0, 8))

        self._scan_btn = ttk.Button(control, text="Scan", style="Accent.TButton",
                                    command=self._scan)
        self._scan_btn.grid(row=0, column=6)

        # Indeterminate progress bar — hidden until a scan is running.
        self._progress = ttk.Progressbar(self, mode="indeterminate", length=200)

        self.fig = Figure(figsize=(7, 5), facecolor=BG_DARK)
        self.ax = self.fig.add_subplot(111, facecolor=BG_PANEL)
        _style_axes(self.ax)

        self.canvas = FigureCanvasTkAgg(self.fig, master=self)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        tb_frame = ttk.Frame(self)
        tb_frame.pack(fill=tk.X)
        toolbar = NavigationToolbar2Tk(self.canvas, tb_frame)
        toolbar.config(bg=BG_PANEL)
        toolbar.update()

    def _scan(self) -> None:
        try:
            start = int(self._start_var.get())
            end = int(self._end_var.get())
            if start < 1 or start > end:
                raise ValueError
        except ValueError:
            messagebox.showerror("Invalid range",
                                 "Enter valid integers with start ≥ 1 and start ≤ end.")
            return

        if end - start > 10_000:
            if not messagebox.askyesno(
                "Large range",
                f"Scanning {end - start + 1:,} values may take a while. Continue?",
            ):
                return

        plot_key = _SCAN_PLOT_KEYS[self._plot_label.get()]
        self._scan_btn.configure(state="disabled")
        self._progress.pack(fill=tk.X, padx=6, pady=(0, 4))
        self._progress.start(10)
        self._app._status_var.set(f"Scanning [{start:,}, {end:,}] …")
        self._app.update_idletasks()

        result_q: _queue.Queue = _queue.Queue()

        def worker() -> None:
            ns = list(range(start, end + 1))
            try:
                if plot_key == "stopping_time":
                    times = [total_stopping_time(n) for n in ns]
                    result_q.put(("stopping_time", ns, times))
                elif plot_key == "altitude":
                    stats_list = [compute_stats(n) for n in ns]
                    altitudes = [s.altitude for s in stats_list]
                    stop_times = [s.stopping_time for s in stats_list]
                    result_q.put(("altitude", ns, altitudes, stop_times))
                elif plot_key == "heatmap_stop":
                    times = [total_stopping_time(n) for n in ns]
                    result_q.put(("heatmap_stop", ns, times))
                elif plot_key == "heatmap_alt":
                    stats_list = [compute_stats(n) for n in ns]
                    altitudes = [s.altitude for s in stats_list]
                    result_q.put(("heatmap_alt", ns, altitudes))
                elif plot_key == "records":
                    times = [total_stopping_time(n) for n in ns]
                    result_q.put(("records", ns, times))
                elif plot_key == "fingerprint":
                    # Subsample if range is too large to display usefully.
                    if len(ns) > _FINGERPRINT_CAP:
                        step = len(ns) // _FINGERPRINT_CAP
                        ns = ns[::step]
                    seqs = [sequence(n) for n in ns]
                    result_q.put(("fingerprint", ns, seqs))
            except Exception as exc:  # noqa: BLE001
                result_q.put(("error", str(exc)))

        threading.Thread(target=worker, daemon=True).start()
        self._poll(result_q, start, end)

    def _poll(self, q: _queue.Queue, start: int, end: int) -> None:
        """Called on the main thread every 100 ms until the worker is done."""
        try:
            data = q.get_nowait()
        except _queue.Empty:
            self.after(100, lambda: self._poll(q, start, end))
            return

        self._progress.stop()
        self._progress.pack_forget()
        self._scan_btn.configure(state="normal")

        if data[0] == "error":
            messagebox.showerror("Scan error", data[1])
            self._app._status_var.set("Scan failed.")
            return

        self._draw(data, start, end)

    def _draw(self, data: tuple, start: int, end: int) -> None:
        """Redraw the axes with computed data (runs on main thread)."""
        import math
        self.fig.clf()
        self.ax = self.fig.add_subplot(111, facecolor=BG_PANEL)
        _style_axes(self.ax)

        kind = data[0]
        if kind == "stopping_time":
            _, ns, times = data
            plot_stopping_time_bar(self.ax, ns, times)
        elif kind == "altitude":
            _, ns, altitudes, stop_times = data
            plot_altitude_scatter(self.ax, ns, altitudes, stop_times)
        elif kind in ("heatmap_stop", "heatmap_alt"):
            _, ns, values = data
            cols = max(1, int(math.isqrt(len(ns))))
            label = "Stopping Time" if kind == "heatmap_stop" else "Altitude"
            plot_convergence_heatmap(self.ax, ns, values, cols,
                                     metric_label=label)
        elif kind == "records":
            _, ns, times = data
            plot_record_holders(self.ax, ns, times)
        elif kind == "fingerprint":
            _, ns, seqs = data
            plot_trajectory_fingerprint(self.ax, ns, seqs)

        _style_figure(self.fig)
        self.fig.tight_layout()
        self.canvas.draw()
        self._app._status_var.set(
            f"Scan complete: n ∈ [{start:,}, {end:,}]."
        )


class _CompareTab(ttk.Frame):
    """Tab for comparing multiple sequences side by side."""

    def __init__(self, parent: ttk.Notebook, app: CollatzApp) -> None:
        super().__init__(parent)
        self._app = app
        self._build()

    def _build(self) -> None:
        control = ttk.Frame(self, style="Panel.TFrame")
        control.pack(fill=tk.X, padx=6, pady=6)

        ttk.Label(control, text="Queued:", style="Panel.TLabel").grid(
            row=0, column=0, padx=(0, 6))

        self._list_var = tk.StringVar()
        self._listbox = tk.Listbox(
            control,
            listvariable=self._list_var,
            height=3,
            bg=BG_INPUT,
            fg=FG_TEXT,
            selectbackground=FG_ACCENT,
            selectforeground=BG_DARK,
            relief="flat",
            width=40,
        )
        self._listbox.grid(row=0, column=1, padx=(0, 6))

        ttk.Button(control, text="Remove", command=self._remove_selected
                   ).grid(row=0, column=2, padx=(0, 4))
        ttk.Button(control, text="Clear all", command=self._clear_all
                   ).grid(row=0, column=3, padx=(0, 8))

        self._log_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(control, text="Log scale",
                        variable=self._log_var).grid(row=0, column=4, padx=(0, 8))

        ttk.Button(control, text="Plot", style="Accent.TButton",
                   command=self._plot).grid(row=0, column=5)

        self.fig = Figure(figsize=(7, 5), facecolor=BG_DARK)
        self.ax = self.fig.add_subplot(111, facecolor=BG_PANEL)
        _style_axes(self.ax)

        self.canvas = FigureCanvasTkAgg(self.fig, master=self)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        tb_frame = ttk.Frame(self)
        tb_frame.pack(fill=tk.X)
        toolbar = NavigationToolbar2Tk(self.canvas, tb_frame)
        toolbar.config(bg=BG_PANEL)
        toolbar.update()

    def refresh_list(self, ns: list[int]) -> None:
        self._listbox.delete(0, tk.END)
        for n in ns:
            self._listbox.insert(tk.END, f"  {n:,}")

    def _remove_selected(self) -> None:
        sel = self._listbox.curselection()
        if not sel:
            return
        idx = sel[0]
        if 0 <= idx < len(self._app._compare_ns):
            self._app._compare_ns.pop(idx)
        self.refresh_list(self._app._compare_ns)

    def _clear_all(self) -> None:
        self._app._compare_ns.clear()
        self.refresh_list([])

    def _plot(self) -> None:
        ns = self._app._compare_ns
        if not ns:
            messagebox.showinfo("Nothing to compare",
                                "Use '+ Compare' on the left panel to queue sequences.")
            return
        self.fig.clf()
        self.ax = self.fig.add_subplot(111, facecolor=BG_PANEL)
        _style_axes(self.ax)
        plot_multi_trajectory(self.ax, ns, log_scale=self._log_var.get())
        _style_figure(self.fig)
        self.fig.tight_layout()
        self.canvas.draw()


def run() -> None:
    """Launch the Collatz Explorer application."""
    app = CollatzApp()
    app.mainloop()
