"""
Collatz sequence visualization helpers.

All functions in this module accept a matplotlib Axes object and draw into
it — they do not create Figure objects themselves.  The GUI (gui/app.py)
handles figure creation, embedding, and lifecycle.

Each single-sequence plot accepts an optional ``seq`` parameter.  Pass a
pre-computed sequence to avoid redundant work when switching between plot
types for the same starting value.

Available plot types
--------------------
plot_trajectory          : Classic value-vs-step line plot (linear scale).
plot_log_trajectory      : Same plot with a log₁₀ y-axis.
plot_phase_portrait      : Phase portrait: seq[k] vs seq[k+1].
plot_log_phase_portrait  : Phase portrait on log–log axes.
plot_stopping_time_bar   : Bar chart of stopping times over a range.
plot_altitude_scatter    : Scatter plot of altitude (peak/n) over a range.
plot_multi_trajectory    : Overlay multiple sequences on one axes.
plot_convergence_heatmap : 2-D colour map of a metric over a grid of n values.
"""

from __future__ import annotations

import copy
import math
import statistics

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.axes import Axes
from matplotlib.colors import ListedColormap

from collatz.core import sequence, total_stopping_time
from collatz.analysis import compute_stats

# Two-colour raster maps reused across parity plots
_PARITY_CMAP = ListedColormap(["#89b4fa", "#f38ba8"])  # blue=even, red=odd


# ---------------------------------------------------------------------------
# Single-sequence plots
# ---------------------------------------------------------------------------

def plot_trajectory(
    ax: Axes,
    n: int,
    *,
    seq: list[int] | None = None,
    color: str = "#1f77b4",
    highlight_peak: bool = True,
    highlight_start: bool = True,
) -> None:
    """Draw the Collatz trajectory as a line plot on linear scale.

    Args:
        ax             : Matplotlib Axes to draw on.
        n              : Starting value.
        seq            : Pre-computed sequence (computed internally if omitted).
        color          : Line colour.
        highlight_peak : If True, mark the peak value with a red dot.
        highlight_start: If True, mark the starting value with a green dot.
    """
    if seq is None:
        seq = sequence(n)
    steps = list(range(len(seq)))

    ax.plot(steps, seq, color=color, linewidth=1.2, zorder=2)

    if highlight_start:
        ax.scatter([0], [seq[0]], color="#2ca02c", zorder=5, s=60,
                   label=f"Start: {seq[0]:,}")

    if highlight_peak:
        peak_idx = int(np.argmax(seq))
        ax.scatter([peak_idx], [seq[peak_idx]], color="#d62728", zorder=5,
                   s=60, label=f"Peak: {seq[peak_idx]:,} (step {peak_idx})")

    ax.set_xlabel("Step")
    ax.set_ylabel("Value")
    ax.set_title(f"Collatz Trajectory  —  n = {n:,}")
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3)


def plot_log_trajectory(
    ax: Axes,
    n: int,
    *,
    seq: list[int] | None = None,
    color: str = "#1f77b4",
    highlight_peak: bool = True,
) -> None:
    """Draw the Collatz trajectory with a log₁₀ y-axis.

    The log scale reveals the oscillation structure that is compressed on a
    linear scale when peaks are very large.

    Args:
        ax            : Matplotlib Axes to draw on.
        n             : Starting value.
        seq           : Pre-computed sequence (computed internally if omitted).
        color         : Line colour.
        highlight_peak: If True, mark the peak value.
    """
    if seq is None:
        seq = sequence(n)
    steps = list(range(len(seq)))

    ax.semilogy(steps, seq, color=color, linewidth=1.2, zorder=2)

    if highlight_peak:
        peak_idx = int(np.argmax(seq))
        ax.scatter([peak_idx], [seq[peak_idx]], color="#d62728", zorder=5,
                   s=60, label=f"Peak: {seq[peak_idx]:,}")

    ax.set_xlabel("Step")
    ax.set_ylabel("Value (log₁₀ scale)")
    ax.set_title(f"Collatz Trajectory (log scale)  —  n = {n:,}")
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3, which="both")


def plot_phase_portrait(
    ax: Axes,
    n: int,
    *,
    seq: list[int] | None = None,
    colormap: str = "plasma",
) -> None:
    """Draw the phase portrait: seq[k] plotted against seq[k+1].

    Points are coloured by step index so direction of travel is visible.

    Args:
        ax       : Matplotlib Axes to draw on.
        n        : Starting value.
        seq      : Pre-computed sequence (computed internally if omitted).
        colormap : Matplotlib colormap name for step-index colouring.
    """
    if seq is None:
        seq = sequence(n)
    x = seq[:-1]
    y = seq[1:]
    steps = np.arange(len(x))

    scatter = ax.scatter(x, y, c=steps, cmap=colormap, s=8, alpha=0.7)
    plt.colorbar(scatter, ax=ax, label="Step index")

    ax.set_xlabel("seq[k]")
    ax.set_ylabel("seq[k+1]")
    ax.set_title(f"Phase Portrait  —  n = {n:,}")
    ax.grid(True, alpha=0.3)


def plot_log_phase_portrait(
    ax: Axes,
    n: int,
    *,
    seq: list[int] | None = None,
    colormap: str = "plasma",
) -> None:
    """Phase portrait on log–log axes.

    The log–log view linearises the two branches of the Collatz map:
    even steps appear as a line with slope 1 through the origin, and
    odd steps follow a roughly linear band as well.

    Args:
        ax       : Matplotlib Axes to draw on.
        n        : Starting value.
        seq      : Pre-computed sequence (computed internally if omitted).
        colormap : Matplotlib colormap name.
    """
    if seq is None:
        seq = sequence(n)
    x = seq[:-1]
    y = seq[1:]
    steps = np.arange(len(x))

    scatter = ax.scatter(x, y, c=steps, cmap=colormap, s=8, alpha=0.7)
    ax.set_xscale("log")
    ax.set_yscale("log")
    plt.colorbar(scatter, ax=ax, label="Step index")

    ax.set_xlabel("seq[k]  (log)")
    ax.set_ylabel("seq[k+1]  (log)")
    ax.set_title(f"Log–Log Phase Portrait  —  n = {n:,}")
    ax.grid(True, alpha=0.3, which="both")


# ---------------------------------------------------------------------------
# Range / comparative plots
# ---------------------------------------------------------------------------

def plot_stopping_time_bar(
    ax: Axes,
    ns: list[int],
    times: list[int],
    *,
    highlight_max: bool = True,
) -> None:
    """Bar chart of pre-computed total stopping times.

    Args:
        ax           : Matplotlib Axes to draw on.
        ns           : List of starting values (x-axis).
        times        : Corresponding stopping times.
        highlight_max: Colour the bar with the longest stopping time in red.
    """
    colors = ["#1f77b4"] * len(ns)
    if highlight_max and times:
        colors[int(np.argmax(times))] = "#d62728"

    width = max(1, (ns[-1] - ns[0]) / 200) if len(ns) > 1 else 1
    ax.bar(ns, times, color=colors, width=width)
    ax.set_xlabel("Starting value n")
    ax.set_ylabel("Stopping time (steps to reach 1)")
    ax.set_title(f"Stopping Times  —  n ∈ [{ns[0]:,}, {ns[-1]:,}]")
    ax.grid(True, axis="y", alpha=0.3)


def plot_altitude_scatter(
    ax: Axes,
    ns: list[int],
    altitudes: list[float],
    stop_times: list[int],
    *,
    colormap: str = "viridis",
) -> None:
    """Scatter plot of pre-computed altitude values.

    Args:
        ax         : Matplotlib Axes to draw on.
        ns         : List of starting values (x-axis).
        altitudes  : Corresponding altitude values (peak / n).
        stop_times : Corresponding stopping times (used for colour).
        colormap   : Colormap for stopping-time colouring.
    """
    scatter = ax.scatter(ns, altitudes, c=stop_times, cmap=colormap,
                         s=10, alpha=0.7)
    plt.colorbar(scatter, ax=ax, label="Stopping time")
    ax.set_xlabel("Starting value n")
    ax.set_ylabel("Altitude  (peak / n)")
    ax.set_title(f"Altitude  —  n ∈ [{ns[0]:,}, {ns[-1]:,}]")
    ax.grid(True, alpha=0.3)


def plot_multi_trajectory(
    ax: Axes,
    ns: list[int],
    *,
    log_scale: bool = False,
    alpha: float = 0.7,
) -> None:
    """Overlay trajectories for multiple starting values on one axes.

    Args:
        ax        : Matplotlib Axes to draw on.
        ns        : List of starting values.
        log_scale : Use log y-axis if True.
        alpha     : Line opacity (useful when many sequences overlap).
    """
    cmap = matplotlib.colormaps["tab10"]
    for i, n in enumerate(ns):
        seq = sequence(n)
        color = cmap(i % 10)
        if log_scale:
            ax.semilogy(range(len(seq)), seq, color=color, alpha=alpha,
                        linewidth=1.0, label=str(n))
        else:
            ax.plot(range(len(seq)), seq, color=color, alpha=alpha,
                    linewidth=1.0, label=str(n))

    ax.set_xlabel("Step")
    ax.set_ylabel("Value" + (" (log scale)" if log_scale else ""))
    ax.set_title("Multi-Sequence Comparison")
    ax.legend(fontsize=7, title="n", loc="upper right")
    ax.grid(True, alpha=0.3)


def plot_convergence_heatmap(
    ax: Axes,
    ns: list[int],
    values: list[float],
    cols: int,
    metric_label: str = "Stopping Time",
) -> None:
    """2-D heatmap where each cell represents a starting value.

    Starting values are laid out in row-major order: ns[0] is the
    bottom-left cell, ns[cols-1] is the end of the first row, etc.

    Args:
        ax           : Matplotlib Axes to draw on.
        ns           : Flat list of starting values.
        values       : Corresponding metric values (same length as ns).
        cols         : Number of columns in the grid.
        metric_label : Label for the colorbar.
    """
    rows = math.ceil(len(values) / cols)
    # Pad to fill the grid if the range doesn't divide evenly.
    padded = list(values) + [float("nan")] * (rows * cols - len(values))
    data = np.array(padded, dtype=float).reshape(rows, cols)

    im = ax.imshow(data, aspect="auto", origin="lower", cmap="inferno")
    plt.colorbar(im, ax=ax, label=metric_label)

    start, end = ns[0], ns[-1]
    ax.set_xlabel(f"Column  (n mod {cols})")
    ax.set_ylabel(f"Row  (n // {cols})")
    ax.set_title(
        f"Heatmap: {metric_label}  —  n ∈ [{start:,}, {end:,}]"
    )


# ---------------------------------------------------------------------------
# Parity & rhythm plots  (single sequence)
# ---------------------------------------------------------------------------

def plot_parity_raster(
    ax: Axes,
    n: int,
    *,
    seq: list[int] | None = None,
) -> None:
    """Horizontal raster showing the even/odd parity word of the sequence.

    Each cell represents one step: blue for an even value (÷2) and red for
    an odd value (×3+1).  A dashed line marks the glide boundary — the step
    where the sequence first drops below n.

    Args:
        ax : Matplotlib Axes.
        n  : Starting value.
        seq: Pre-computed sequence (optional).
    """
    if seq is None:
        seq = sequence(n)
    if len(seq) < 2:
        ax.text(0.5, 0.5, "Sequence too short to display.",
                ha="center", va="center", transform=ax.transAxes)
        return

    parity = np.array([0 if v % 2 == 0 else 1 for v in seq[:-1]])
    ax.imshow(parity.reshape(1, -1), aspect="auto", cmap=_PARITY_CMAP,
              vmin=0, vmax=1, interpolation="nearest",
              extent=[0, len(parity), 0, 1])

    # Glide marker
    glide_step = next((i for i, v in enumerate(seq) if v < n), len(seq) - 1)
    if 0 < glide_step < len(parity):
        ax.axvline(glide_step, color="#f9e2af", linestyle="--", linewidth=1.4,
                   label=f"Glide = {glide_step}")
        ax.legend(fontsize=7, loc="upper right")

    odd_count = int(parity.sum())
    ax.set_title(
        f"Parity Word  —  n = {n:,}   "
        f"(blue = ÷2,  red = ×3+1,  {odd_count} odd steps / {len(parity)} total)"
    )
    ax.set_xlabel("Step")
    ax.set_yticks([])


def plot_bit_length_walk(
    ax: Axes,
    n: int,
    *,
    seq: list[int] | None = None,
) -> None:
    """Plot the bit-length of each sequence value as a random walk.

    Each odd step increases the bit-length by ≈ log₂(3) ≈ 1.585; each even
    step decreases it by exactly 1.  The walk must eventually reach 0
    (equivalent to the Collatz conjecture).

    Args:
        ax : Matplotlib Axes.
        n  : Starting value.
        seq: Pre-computed sequence (optional).
    """
    if seq is None:
        seq = sequence(n)

    bits = [v.bit_length() for v in seq]
    steps = list(range(len(bits)))

    ax.plot(steps, bits, color="#89b4fa", linewidth=1.0, zorder=3)
    ax.fill_between(steps, bits, alpha=0.12, color="#89b4fa")
    ax.axhline(n.bit_length(), color="#6c7086", linestyle="--", linewidth=1.0,
               label=f"Start: {n.bit_length()} bits")

    # Annotate the theoretical per-step drift
    if len(seq) > 1:
        odd_frac = sum(1 for v in seq[:-1] if v % 2 != 0) / (len(seq) - 1)
        drift = odd_frac * math.log2(3) + (1 - odd_frac) * (-1)
        ax.text(0.98, 0.96,
                f"odd fraction: {odd_frac:.2%}\ndrift/step: {drift:+.3f} bits",
                transform=ax.transAxes, ha="right", va="top", fontsize=7,
                color="#cdd6f4")

    ax.set_xlabel("Step")
    ax.set_ylabel("Bit length  ⌊log₂ n⌋ + 1")
    ax.set_title(f"Bit-Length Random Walk  —  n = {n:,}")
    ax.legend(fontsize=7)
    ax.grid(True, alpha=0.3)


def plot_odd_step_gaps(
    ax: Axes,
    n: int,
    *,
    seq: list[int] | None = None,
) -> None:
    """Histogram of gaps (in steps) between consecutive odd-step applications.

    A gap of k means k consecutive even steps separate two ×3+1 applications.
    Most gaps are 1–2; larger gaps indicate a long run of pure halving.

    Args:
        ax : Matplotlib Axes.
        n  : Starting value.
        seq: Pre-computed sequence (optional).
    """
    if seq is None:
        seq = sequence(n)

    odd_pos = [i for i, v in enumerate(seq[:-1]) if v % 2 != 0]
    if len(odd_pos) < 2:
        ax.text(0.5, 0.5,
                "Fewer than two odd steps — no gaps to display.",
                ha="center", va="center", transform=ax.transAxes)
        ax.set_title(f"Odd-Step Gap Distribution  —  n = {n:,}")
        return

    gaps = [odd_pos[i + 1] - odd_pos[i] for i in range(len(odd_pos) - 1)]
    max_gap = max(gaps)
    bins = list(range(1, max_gap + 2))

    ax.hist(gaps, bins=bins, color="#f9e2af", edgecolor="#1e1e2e",
            linewidth=0.5, align="left")
    mean_gap = statistics.mean(gaps)
    ax.axvline(mean_gap, color="#f38ba8", linestyle="--", linewidth=1.4,
               label=f"Mean = {mean_gap:.2f}")

    ax.set_xlabel("Gap between consecutive odd steps (steps)")
    ax.set_ylabel("Frequency")
    ax.set_title(
        f"Odd-Step Gap Distribution  —  n = {n:,}   ({len(odd_pos)} odd steps)"
    )
    ax.legend(fontsize=7)
    ax.grid(True, axis="y", alpha=0.3)


# ---------------------------------------------------------------------------
# Range plots  (new types)
# ---------------------------------------------------------------------------

def plot_record_holders(
    ax: Axes,
    ns: list[int],
    times: list[int],
) -> None:
    """Scatter stopping times; highlight and connect record-breaking values.

    A record-holder is any n whose stopping time exceeds every smaller n in
    the scan range.  The step-function envelope shows how long each record
    stands before being surpassed.

    Args:
        ax   : Matplotlib Axes.
        ns   : Starting values (sorted ascending).
        times: Corresponding stopping times.
    """
    # Background scatter
    ax.scatter(ns, times, s=4, alpha=0.35, color="#585b70", zorder=2,
               linewidths=0)

    # Find records
    rec_ns: list[int] = []
    rec_ts: list[int] = []
    best = -1
    for n, t in zip(ns, times):
        if t > best:
            best = t
            rec_ns.append(n)
            rec_ts.append(t)

    # Step-function envelope
    env_x = rec_ns + [ns[-1]]
    env_y = rec_ts + [rec_ts[-1]]
    ax.step(env_x, env_y, where="post", color="#89b4fa", linewidth=1.2,
            alpha=0.8, zorder=3)
    ax.scatter(rec_ns, rec_ts, s=35, color="#89b4fa", zorder=5,
               label=f"{len(rec_ns)} record-holders")

    ax.set_xlabel("Starting value n")
    ax.set_ylabel("Stopping time")
    ax.set_title(f"Stopping-Time Record Holders  —  n ∈ [{ns[0]:,}, {ns[-1]:,}]")
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3)


def plot_trajectory_fingerprint(
    ax: Axes,
    ns: list[int],
    seqs: list[list[int]],
) -> None:
    """2-D heatmap where each row is a full trajectory coloured by log₂(value).

    The left region shows the divergence phase; the right region shows all
    sequences funnelling into the same attractor paths as they approach 1.
    Cells after a sequence has terminated are shown in black.

    Args:
        ax  : Matplotlib Axes.
        ns  : Starting values (one per row, bottom = ns[0]).
        seqs: Corresponding full sequences — one list per n.
    """
    if not seqs:
        return

    max_len = max(len(s) for s in seqs)
    data = np.full((len(seqs), max_len), np.nan)
    for i, s in enumerate(seqs):
        data[i, : len(s)] = np.log2(np.array(s, dtype=float))

    cmap = copy.copy(matplotlib.colormaps["inferno"])
    cmap.set_bad(color="#1e1e2e")

    im = ax.imshow(data, aspect="auto", origin="lower", cmap=cmap,
                   interpolation="nearest")
    plt.colorbar(im, ax=ax, label="log₂(value)")

    # Y-axis: label a handful of n values
    tick_step = max(1, len(ns) // 8)
    tick_pos = list(range(0, len(ns), tick_step))
    ax.set_yticks(tick_pos)
    ax.set_yticklabels([f"{ns[i]:,}" for i in tick_pos], fontsize=7)

    ax.set_xlabel("Step")
    ax.set_ylabel("Starting value n")
    ax.set_title(
        f"Trajectory Fingerprint  —  n ∈ [{ns[0]:,}, {ns[-1]:,}]  "
        f"({len(ns)} trajectories)"
    )
