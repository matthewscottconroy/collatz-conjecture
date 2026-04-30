"""
collatz — Collatz conjecture exploration library.

Sub-modules
-----------
core           : Low-level sequence computation and step function.
analysis       : Statistical metrics (stopping time, altitude, oscillation, etc.).
library        : Curated catalogue of mathematically interesting starting values.
visualization  : Matplotlib helpers for plotting trajectories and range data.
graph_export   : Build and export Collatz graphs (forward and inverse) as PNG,
                 SVG, or CSV files suitable for Gephi/Cytoscape.

Quick start
-----------
>>> from collatz import sequence, compute_stats
>>> sequence(27)[-1]
1
>>> compute_stats(27).stopping_time
111
>>> from collatz import get_predecessors
>>> get_predecessors(10)   # both predecessors of 10
[20, 3]
"""

from collatz.core import (
    CollatzError,
    MAX_ITERATIONS,
    get_predecessors,
    is_power_of_two,
    sequence,
    sequence_iter,
    step,
    total_stopping_time,
)
from collatz.analysis import (
    TrajectoryStats,
    band_persistence,
    compute_stats,
    find_interesting,
    glide,
    near_cycle_score,
    oscillation_index,
)

__version__ = "1.1.0"
__all__ = [
    # core
    "CollatzError",
    "MAX_ITERATIONS",
    "get_predecessors",
    "is_power_of_two",
    "sequence",
    "sequence_iter",
    "step",
    "total_stopping_time",
    # analysis
    "TrajectoryStats",
    "band_persistence",
    "compute_stats",
    "find_interesting",
    "glide",
    "near_cycle_score",
    "oscillation_index",
]
