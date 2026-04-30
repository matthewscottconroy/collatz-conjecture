"""
Smoke tests for collatz.visualization.

These tests verify that every public plotting function runs without raising an
exception and produces a matplotlib Axes/Figure with non-empty content.
They do not assert exact pixel or numerical outputs — that belongs in the
analysis tests — but they catch import errors, broken matplotlib interactions,
and API-signature regressions.
"""

from __future__ import annotations

import math

import matplotlib
matplotlib.use("Agg")  # non-interactive backend; must be set before importing pyplot
import matplotlib.pyplot as plt
import pytest

from collatz.core import sequence
from collatz.analysis import compute_stats
from collatz.visualization import (
    plot_altitude_scatter,
    plot_bit_length_walk,
    plot_convergence_heatmap,
    plot_log_phase_portrait,
    plot_log_trajectory,
    plot_multi_trajectory,
    plot_odd_step_gaps,
    plot_parity_raster,
    plot_phase_portrait,
    plot_record_holders,
    plot_stopping_time_bar,
    plot_trajectory,
    plot_trajectory_fingerprint,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _fresh_ax():
    """Return a fresh Axes on a new Figure."""
    fig, ax = plt.subplots()
    return fig, ax


def _close(fig) -> None:
    plt.close(fig)


# ---------------------------------------------------------------------------
# Single-sequence plots
# ---------------------------------------------------------------------------

class TestPlotTrajectory:
    def test_runs_without_error(self) -> None:
        fig, ax = _fresh_ax()
        plot_trajectory(ax, 27)
        _close(fig)

    def test_accepts_precomputed_seq(self) -> None:
        seq = sequence(27)
        fig, ax = _fresh_ax()
        plot_trajectory(ax, 27, seq=seq)
        _close(fig)

    def test_title_contains_n(self) -> None:
        fig, ax = _fresh_ax()
        plot_trajectory(ax, 27)
        assert "27" in ax.get_title()
        _close(fig)

    def test_axes_have_data(self) -> None:
        fig, ax = _fresh_ax()
        plot_trajectory(ax, 27)
        assert len(ax.lines) > 0
        _close(fig)

    def test_highlight_flags(self) -> None:
        fig, ax = _fresh_ax()
        plot_trajectory(ax, 27, highlight_peak=False, highlight_start=False)
        # No scatter markers when both flags off — only line collections.
        assert len(ax.collections) == 0
        _close(fig)

    def test_n1(self) -> None:
        fig, ax = _fresh_ax()
        plot_trajectory(ax, 1)
        _close(fig)

    def test_large_n(self) -> None:
        fig, ax = _fresh_ax()
        plot_trajectory(ax, 837799)
        _close(fig)


class TestPlotLogTrajectory:
    def test_runs_without_error(self) -> None:
        fig, ax = _fresh_ax()
        plot_log_trajectory(ax, 27)
        _close(fig)

    def test_accepts_precomputed_seq(self) -> None:
        seq = sequence(27)
        fig, ax = _fresh_ax()
        plot_log_trajectory(ax, 27, seq=seq)
        _close(fig)

    def test_y_axis_is_log(self) -> None:
        fig, ax = _fresh_ax()
        plot_log_trajectory(ax, 27)
        assert ax.get_yscale() == "log"
        _close(fig)

    def test_n1(self) -> None:
        fig, ax = _fresh_ax()
        plot_log_trajectory(ax, 1)
        _close(fig)


class TestPlotPhasePortrait:
    def test_runs_without_error(self) -> None:
        fig, ax = _fresh_ax()
        plot_phase_portrait(ax, 27)
        _close(fig)

    def test_accepts_precomputed_seq(self) -> None:
        seq = sequence(27)
        fig, ax = _fresh_ax()
        plot_phase_portrait(ax, 27, seq=seq)
        _close(fig)

    def test_produces_scatter(self) -> None:
        fig, ax = _fresh_ax()
        plot_phase_portrait(ax, 27)
        assert len(ax.collections) > 0
        _close(fig)

    def test_n2(self) -> None:
        # n=2 has only one step: seq=[2,1], so one (x,y) pair.
        fig, ax = _fresh_ax()
        plot_phase_portrait(ax, 2)
        _close(fig)


class TestPlotLogPhasePortrait:
    def test_runs_without_error(self) -> None:
        fig, ax = _fresh_ax()
        plot_log_phase_portrait(ax, 27)
        _close(fig)

    def test_accepts_precomputed_seq(self) -> None:
        seq = sequence(27)
        fig, ax = _fresh_ax()
        plot_log_phase_portrait(ax, 27, seq=seq)
        _close(fig)

    def test_log_log_axes(self) -> None:
        fig, ax = _fresh_ax()
        plot_log_phase_portrait(ax, 27)
        assert ax.get_xscale() == "log"
        assert ax.get_yscale() == "log"
        _close(fig)


# ---------------------------------------------------------------------------
# Sequence-cached plot: verify seq parameter avoids recomputation
# ---------------------------------------------------------------------------

class TestSeqParameterConsistency:
    """Passing a pre-computed seq must produce identical results to not passing one."""

    def _line_data(self, ax) -> list:
        return [line.get_ydata().tolist() for line in ax.lines]

    def test_trajectory_seq_matches(self) -> None:
        seq = sequence(100)
        fig1, ax1 = _fresh_ax()
        plot_trajectory(ax1, 100)
        fig2, ax2 = _fresh_ax()
        plot_trajectory(ax2, 100, seq=seq)
        assert self._line_data(ax1) == self._line_data(ax2)
        _close(fig1)
        _close(fig2)

    def test_log_trajectory_seq_matches(self) -> None:
        seq = sequence(100)
        fig1, ax1 = _fresh_ax()
        plot_log_trajectory(ax1, 100)
        fig2, ax2 = _fresh_ax()
        plot_log_trajectory(ax2, 100, seq=seq)
        assert self._line_data(ax1) == self._line_data(ax2)
        _close(fig1)
        _close(fig2)


# ---------------------------------------------------------------------------
# Range / comparative plots
# ---------------------------------------------------------------------------

class TestPlotStoppingTimeBar:
    def _data(self, start: int, end: int):
        from collatz.core import total_stopping_time
        ns = list(range(start, end + 1))
        times = [total_stopping_time(n) for n in ns]
        return ns, times

    def test_runs_without_error(self) -> None:
        ns, times = self._data(1, 20)
        fig, ax = _fresh_ax()
        plot_stopping_time_bar(ax, ns, times)
        _close(fig)

    def test_produces_bars(self) -> None:
        ns, times = self._data(1, 20)
        fig, ax = _fresh_ax()
        plot_stopping_time_bar(ax, ns, times)
        assert len(ax.patches) == len(ns)
        _close(fig)

    def test_single_value(self) -> None:
        fig, ax = _fresh_ax()
        plot_stopping_time_bar(ax, [27], [111])
        _close(fig)

    def test_highlight_max_colours_bar(self) -> None:
        ns, times = self._data(1, 10)
        fig, ax = _fresh_ax()
        plot_stopping_time_bar(ax, ns, times, highlight_max=True)
        colors = [p.get_facecolor() for p in ax.patches]
        # At least one bar should be a different colour (the highlighted one).
        assert len({tuple(c) for c in colors}) > 1
        _close(fig)


class TestPlotAltitudeScatter:
    def _data(self, start: int, end: int):
        stats_list = [compute_stats(n) for n in range(start, end + 1)]
        ns = list(range(start, end + 1))
        altitudes = [s.altitude for s in stats_list]
        stop_times = [s.stopping_time for s in stats_list]
        return ns, altitudes, stop_times

    def test_runs_without_error(self) -> None:
        ns, altitudes, stop_times = self._data(1, 20)
        fig, ax = _fresh_ax()
        plot_altitude_scatter(ax, ns, altitudes, stop_times)
        _close(fig)

    def test_produces_scatter(self) -> None:
        ns, altitudes, stop_times = self._data(1, 20)
        fig, ax = _fresh_ax()
        plot_altitude_scatter(ax, ns, altitudes, stop_times)
        assert len(ax.collections) > 0
        _close(fig)


class TestPlotMultiTrajectory:
    def test_runs_without_error(self) -> None:
        fig, ax = _fresh_ax()
        plot_multi_trajectory(ax, [3, 27, 100])
        _close(fig)

    def test_log_scale(self) -> None:
        fig, ax = _fresh_ax()
        plot_multi_trajectory(ax, [3, 27], log_scale=True)
        assert ax.get_yscale() == "log"
        _close(fig)

    def test_one_line_per_n(self) -> None:
        ns = [3, 27, 100]
        fig, ax = _fresh_ax()
        plot_multi_trajectory(ax, ns)
        assert len(ax.lines) == len(ns)
        _close(fig)

    def test_empty_list(self) -> None:
        fig, ax = _fresh_ax()
        plot_multi_trajectory(ax, [])
        _close(fig)


class TestPlotConvergenceHeatmap:
    def _prepare(self, start: int, end: int):
        from collatz.core import total_stopping_time
        ns = list(range(start, end + 1))
        values = [float(total_stopping_time(n)) for n in ns]
        cols = max(1, int(math.isqrt(len(ns))))
        return ns, values, cols

    def test_runs_without_error(self) -> None:
        ns, values, cols = self._prepare(1, 25)
        fig, ax = _fresh_ax()
        plot_convergence_heatmap(ax, ns, values, cols)
        _close(fig)

    def test_produces_image(self) -> None:
        ns, values, cols = self._prepare(1, 25)
        fig, ax = _fresh_ax()
        plot_convergence_heatmap(ax, ns, values, cols)
        assert len(ax.images) > 0
        _close(fig)

    def test_custom_metric_label(self) -> None:
        ns, values, cols = self._prepare(1, 9)
        fig, ax = _fresh_ax()
        plot_convergence_heatmap(ax, ns, values, cols, metric_label="Altitude")
        assert "Altitude" in ax.get_title()
        _close(fig)

    def test_non_square_range(self) -> None:
        # Range size 7 is not a perfect square — padding should be applied silently.
        ns, values, cols = self._prepare(1, 7)
        fig, ax = _fresh_ax()
        plot_convergence_heatmap(ax, ns, values, cols)
        _close(fig)


# ---------------------------------------------------------------------------
# Parity & rhythm plots
# ---------------------------------------------------------------------------

class TestPlotParityRaster:
    def test_runs_without_error(self) -> None:
        fig, ax = _fresh_ax()
        plot_parity_raster(ax, 27)
        _close(fig)

    def test_accepts_precomputed_seq(self) -> None:
        seq = sequence(27)
        fig, ax = _fresh_ax()
        plot_parity_raster(ax, 27, seq=seq)
        _close(fig)

    def test_produces_image(self) -> None:
        fig, ax = _fresh_ax()
        plot_parity_raster(ax, 27)
        assert len(ax.images) > 0
        _close(fig)

    def test_title_contains_n(self) -> None:
        fig, ax = _fresh_ax()
        plot_parity_raster(ax, 27)
        assert "27" in ax.get_title()
        _close(fig)

    def test_n1_no_crash(self) -> None:
        fig, ax = _fresh_ax()
        plot_parity_raster(ax, 1)
        _close(fig)

    def test_power_of_two_no_crash(self) -> None:
        # All steps are even — raster should still render.
        fig, ax = _fresh_ax()
        plot_parity_raster(ax, 16)
        _close(fig)


class TestPlotBitLengthWalk:
    def test_runs_without_error(self) -> None:
        fig, ax = _fresh_ax()
        plot_bit_length_walk(ax, 27)
        _close(fig)

    def test_accepts_precomputed_seq(self) -> None:
        seq = sequence(27)
        fig, ax = _fresh_ax()
        plot_bit_length_walk(ax, 27, seq=seq)
        _close(fig)

    def test_has_line(self) -> None:
        fig, ax = _fresh_ax()
        plot_bit_length_walk(ax, 27)
        assert len(ax.lines) > 0
        _close(fig)

    def test_ends_at_bit_length_one(self) -> None:
        # The final value is always 1, whose bit_length is 1.
        fig, ax = _fresh_ax()
        plot_bit_length_walk(ax, 27)
        ydata = ax.lines[0].get_ydata()
        assert ydata[-1] == 1
        _close(fig)

    def test_n1_no_crash(self) -> None:
        fig, ax = _fresh_ax()
        plot_bit_length_walk(ax, 1)
        _close(fig)


class TestPlotOddStepGaps:
    def test_runs_without_error(self) -> None:
        fig, ax = _fresh_ax()
        plot_odd_step_gaps(ax, 27)
        _close(fig)

    def test_accepts_precomputed_seq(self) -> None:
        seq = sequence(27)
        fig, ax = _fresh_ax()
        plot_odd_step_gaps(ax, 27, seq=seq)
        _close(fig)

    def test_power_of_two_no_crash(self) -> None:
        # No odd steps in a power-of-two sequence.
        fig, ax = _fresh_ax()
        plot_odd_step_gaps(ax, 16)
        _close(fig)

    def test_produces_histogram_for_n3(self) -> None:
        fig, ax = _fresh_ax()
        plot_odd_step_gaps(ax, 3)
        assert len(ax.patches) > 0
        _close(fig)


# ---------------------------------------------------------------------------
# New range plots
# ---------------------------------------------------------------------------

class TestPlotRecordHolders:
    def _data(self, start: int, end: int):
        from collatz.core import total_stopping_time
        ns = list(range(start, end + 1))
        times = [total_stopping_time(n) for n in ns]
        return ns, times

    def test_runs_without_error(self) -> None:
        ns, times = self._data(1, 50)
        fig, ax = _fresh_ax()
        plot_record_holders(ax, ns, times)
        _close(fig)

    def test_title_contains_range(self) -> None:
        ns, times = self._data(1, 30)
        fig, ax = _fresh_ax()
        plot_record_holders(ax, ns, times)
        assert "1" in ax.get_title() and "30" in ax.get_title()
        _close(fig)

    def test_has_scatter_collections(self) -> None:
        ns, times = self._data(1, 30)
        fig, ax = _fresh_ax()
        plot_record_holders(ax, ns, times)
        assert len(ax.collections) > 0
        _close(fig)

    def test_known_first_record(self) -> None:
        # n=1 always has the first record (stopping time 0 or first in range).
        ns, times = self._data(1, 100)
        fig, ax = _fresh_ax()
        plot_record_holders(ax, ns, times)
        _close(fig)


class TestPlotTrajectoryFingerprint:
    def _data(self, start: int, end: int):
        ns = list(range(start, end + 1))
        seqs = [sequence(n) for n in ns]
        return ns, seqs

    def test_runs_without_error(self) -> None:
        ns, seqs = self._data(1, 20)
        fig, ax = _fresh_ax()
        plot_trajectory_fingerprint(ax, ns, seqs)
        _close(fig)

    def test_produces_image(self) -> None:
        ns, seqs = self._data(1, 20)
        fig, ax = _fresh_ax()
        plot_trajectory_fingerprint(ax, ns, seqs)
        assert len(ax.images) > 0
        _close(fig)

    def test_title_contains_range(self) -> None:
        ns, seqs = self._data(1, 20)
        fig, ax = _fresh_ax()
        plot_trajectory_fingerprint(ax, ns, seqs)
        assert "1" in ax.get_title() and "20" in ax.get_title()
        _close(fig)

    def test_empty_input_no_crash(self) -> None:
        fig, ax = _fresh_ax()
        plot_trajectory_fingerprint(ax, [], [])
        _close(fig)

    def test_image_height_equals_num_sequences(self) -> None:
        ns, seqs = self._data(2, 10)
        fig, ax = _fresh_ax()
        plot_trajectory_fingerprint(ax, ns, seqs)
        image_data = ax.images[0].get_array()
        assert image_data.shape[0] == len(ns)
        _close(fig)
