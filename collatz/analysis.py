"""
Statistical analysis of Collatz sequences.

This module provides functions for measuring properties that characterise
how "interesting" a sequence is, including trajectory length, peak values,
oscillation behaviour, glide length, and near-cycle detection.

Glossary
--------
stopping_time      : Total steps until the sequence reaches 1.
peak_value         : Maximum value encountered in the sequence.
altitude           : peak_value / n  — how high the sequence climbs relative
                     to its start.
glide              : Steps until the sequence first reaches a value < n.
oscillation_index  : Fraction of steps that are local maxima, indicating
                     how frequently the sequence reverses direction.
band_persistence   : Longest fraction of the sequence that remains within a
                     narrow value band — high values hint at near-cyclic
                     behaviour.
near_cycle_score   : 0-1 score; higher means the sequence's local-maxima
                     envelope decays slowly (looks "almost periodic").
"""

from __future__ import annotations

import math
import statistics
from collections import deque
from dataclasses import dataclass, field
from typing import Callable

from collatz.core import sequence, total_stopping_time, CollatzError


# ---------------------------------------------------------------------------
# Data container
# ---------------------------------------------------------------------------

@dataclass
class TrajectoryStats:
    """All key statistics for a single starting value.

    Attributes:
        n                    : Starting value.
        seq                  : Full sequence list [n, ..., 1].
        length               : Total number of elements (= stopping_time + 1).
        stopping_time        : Steps to reach 1.
        glide                : Steps until first value < n.
        peak_value           : Maximum value in the sequence.
        altitude             : peak_value / n.
        oscillation_index    : Local-maxima count / (length - 2).
        band_persistence     : Longest narrow-band window as a fraction.
        near_cycle_score     : 0-1 near-periodicity score.
        even_steps           : Count of even-to-even/2 steps.
        odd_steps            : Count of odd-to-3n+1 steps.
        odd_fraction         : odd_steps / stopping_time.
    """

    n: int
    seq: list[int]
    length: int = field(init=False)
    stopping_time: int = field(init=False)
    glide: int = field(init=False)
    peak_value: int = field(init=False)
    altitude: float = field(init=False)
    oscillation_index: float = field(init=False)
    band_persistence: float = field(init=False)
    near_cycle_score: float = field(init=False)
    even_steps: int = field(init=False)
    odd_steps: int = field(init=False)
    odd_fraction: float = field(init=False)

    def __post_init__(self) -> None:
        s = self.seq
        self.length = len(s)
        self.stopping_time = len(s) - 1
        self.peak_value = max(s)
        self.altitude = self.peak_value / self.n if self.n != 0 else 0.0
        self.glide = _compute_glide(s)
        self.oscillation_index = _compute_oscillation_index(s)
        self.band_persistence = _compute_band_persistence(s)
        self.near_cycle_score = _compute_near_cycle_score(s)
        self.even_steps = sum(1 for v in s[:-1] if v % 2 == 0)
        self.odd_steps = sum(1 for v in s[:-1] if v % 2 != 0)
        self.odd_fraction = (
            self.odd_steps / self.stopping_time if self.stopping_time > 0 else 0.0
        )

    def summary(self) -> str:
        """Return a human-readable summary string."""
        return (
            f"n={self.n:,}\n"
            f"  Stopping time     : {self.stopping_time:,}\n"
            f"  Peak value        : {self.peak_value:,}\n"
            f"  Altitude (peak/n) : {self.altitude:.2f}×\n"
            f"  Glide             : {self.glide:,}\n"
            f"  Oscillation index : {self.oscillation_index:.4f}\n"
            f"  Band persistence  : {self.band_persistence:.4f}\n"
            f"  Near-cycle score  : {self.near_cycle_score:.4f}\n"
            f"  Odd steps         : {self.odd_steps:,} ({self.odd_fraction:.1%})\n"
            f"  Even steps        : {self.even_steps:,}"
        )


# ---------------------------------------------------------------------------
# Module-level metric dispatch table (built once, not per call)
# ---------------------------------------------------------------------------

_METRIC_FN: dict[str, Callable[[TrajectoryStats], float]] = {
    "stopping_time": lambda s: float(s.stopping_time),
    "altitude": lambda s: s.altitude,
    "oscillation_index": lambda s: s.oscillation_index,
    "band_persistence": lambda s: s.band_persistence,
    "near_cycle_score": lambda s: s.near_cycle_score,
}


# ---------------------------------------------------------------------------
# Primary metric functions
# ---------------------------------------------------------------------------

def compute_stats(n: int, seq: list[int] | None = None) -> TrajectoryStats:
    """Compute all statistics for the Collatz sequence starting at n.

    Args:
        n  : Starting positive integer.
        seq: Pre-computed sequence [n, ..., 1].  If omitted the sequence is
             computed internally.  Pass a cached copy to avoid redundant work
             when the sequence has already been computed by the caller.

    Returns:
        A populated TrajectoryStats dataclass.

    Raises:
        CollatzError: If n is not a positive integer.
    """
    if seq is None:
        seq = sequence(n)
    return TrajectoryStats(n=n, seq=seq)


def glide(n: int) -> int:
    """Return the number of steps until the sequence first drops below n.

    This measures how long n "resists" falling — a large glide relative to
    the total stopping time indicates a slow initial descent.

    Args:
        n: Starting positive integer.

    Returns:
        Number of steps. Returns 0 if the first step already < n.

    Raises:
        CollatzError: If n <= 0.
    """
    return _compute_glide(sequence(n))


def oscillation_index(n: int) -> float:
    """Fraction of interior sequence elements that are local maxima.

    A local maximum at position i means seq[i] > seq[i-1] and seq[i] > seq[i+1].
    High values (~0.3+) indicate a highly oscillating trajectory.

    Args:
        n: Starting positive integer.

    Returns:
        Value in [0, 1].
    """
    return _compute_oscillation_index(sequence(n))


def band_persistence(n: int, bandwidth_ratio: float = 4.0) -> float:
    """Fraction of the sequence spent within a narrow value band.

    Uses a sliding-window O(N) algorithm to find the longest contiguous
    sub-sequence where max / min <= bandwidth_ratio. High band persistence
    suggests near-cyclic oscillation.

    Args:
        n: Starting positive integer.
        bandwidth_ratio: Maximum allowed ratio max/min within the window.

    Returns:
        Length of best window / total sequence length, in [0, 1].
    """
    return _compute_band_persistence(sequence(n), bandwidth_ratio)


def near_cycle_score(n: int) -> float:
    """0-1 score measuring near-periodicity of the local-maxima envelope.

    Extracts all local maxima, computes the standard deviation of their
    log-values normalised by the mean, then maps to [0, 1] via
    score = exp(-cv²) where cv is the coefficient of variation. A score
    near 1.0 means the maxima are nearly equal (cycle-like); near 0.0
    means they vary wildly.

    Args:
        n: Starting positive integer.

    Returns:
        Score in [0, 1].
    """
    return _compute_near_cycle_score(sequence(n))


def find_interesting(
    start: int,
    end: int,
    metric: str = "stopping_time",
    top_n: int = 10,
    *,
    progress: Callable[[int, int], None] | None = None,
) -> list[tuple[int, float]]:
    """Scan [start, end] and return the top_n most interesting starting values.

    Args:
        start: Inclusive lower bound (must be >= 1).
        end: Inclusive upper bound.
        metric: One of 'stopping_time', 'altitude', 'oscillation_index',
                'band_persistence', 'near_cycle_score'.
        top_n: How many results to return.  If the range contains fewer than
               top_n values all of them are returned.
        progress: Optional callback ``progress(done, total)`` called after each
                  value is processed.  Useful for progress bars in CLI/GUI callers.

    Returns:
        List of (n, score) tuples sorted descending by score.

    Raises:
        ValueError: If start > end, start < 1, or metric is unknown.
    """
    if start < 1:
        raise ValueError("start must be >= 1")
    if start > end:
        raise ValueError("start must be <= end")
    if metric not in _METRIC_FN:
        raise ValueError(
            f"Unknown metric {metric!r}. Choose from: {list(_METRIC_FN)}"
        )
    fn = _METRIC_FN[metric]
    total = end - start + 1
    results: list[tuple[int, float]] = []
    for i, n in enumerate(range(start, end + 1), 1):
        if progress is not None:
            progress(i, total)
        stats = compute_stats(n)
        results.append((n, fn(stats)))
    results.sort(key=lambda t: t[1], reverse=True)
    return results[:top_n]


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _compute_glide(seq: list[int]) -> int:
    n = seq[0]
    for i, v in enumerate(seq):
        if v < n:
            return i
    return len(seq) - 1


def _compute_oscillation_index(seq: list[int]) -> float:
    if len(seq) < 3:
        return 0.0
    interior = seq[1:-1]
    count = sum(
        1
        for i, v in enumerate(interior, start=1)
        if seq[i - 1] < v and v > seq[i + 1]
    )
    return count / len(interior)


def _compute_band_persistence(
    seq: list[int], bandwidth_ratio: float = 4.0
) -> float:
    """O(N) sliding-window band persistence."""
    if not seq:
        return 0.0
    n = len(seq)
    best = 1
    left = 0
    min_dq: deque[int] = deque()
    max_dq: deque[int] = deque()

    for right in range(n):
        while min_dq and seq[min_dq[-1]] >= seq[right]:
            min_dq.pop()
        min_dq.append(right)
        while max_dq and seq[max_dq[-1]] <= seq[right]:
            max_dq.pop()
        max_dq.append(right)

        while seq[max_dq[0]] / seq[min_dq[0]] > bandwidth_ratio:
            left += 1
            if min_dq[0] < left:
                min_dq.popleft()
            if max_dq[0] < left:
                max_dq.popleft()

        best = max(best, right - left + 1)

    return best / n


def _compute_near_cycle_score(seq: list[int]) -> float:
    """Score based on coefficient of variation of log local-maxima values."""
    maxima = [
        seq[i]
        for i in range(1, len(seq) - 1)
        if seq[i] > seq[i - 1] and seq[i] > seq[i + 1]
    ]
    if len(maxima) < 2:
        return 0.0
    log_maxima = [math.log(m) for m in maxima]
    mean = statistics.mean(log_maxima)
    if mean == 0:
        return 0.0
    cv = statistics.stdev(log_maxima) / mean
    return math.exp(-(cv ** 2))
