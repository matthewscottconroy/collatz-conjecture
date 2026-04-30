"""
Tests for the public collatz package API.

These tests verify that everything promised in collatz/__init__.py is actually
importable from the top-level package and behaves correctly.  They are
intentionally shallow — deep correctness is covered in the module-specific
test files — but they catch __all__ mismatches, missing re-exports, and
version-string regressions.
"""

from __future__ import annotations

import importlib
import types

import pytest

import collatz


# ---------------------------------------------------------------------------
# __all__ completeness
# ---------------------------------------------------------------------------

class TestAllExports:
    def test_all_names_importable(self) -> None:
        """Every name listed in __all__ must be importable from collatz."""
        for name in collatz.__all__:
            assert hasattr(collatz, name), (
                f"'{name}' is listed in collatz.__all__ but not importable"
            )

    def test_all_names_not_private(self) -> None:
        for name in collatz.__all__:
            assert not name.startswith("_"), (
                f"Private name '{name}' should not be in __all__"
            )


# ---------------------------------------------------------------------------
# Core symbols
# ---------------------------------------------------------------------------

class TestCoreExports:
    def test_step_imported(self) -> None:
        from collatz import step
        assert callable(step)

    def test_sequence_imported(self) -> None:
        from collatz import sequence
        assert callable(sequence)

    def test_sequence_iter_imported(self) -> None:
        from collatz import sequence_iter
        result = list(collatz.sequence_iter(3))
        assert result == collatz.sequence(3)

    def test_total_stopping_time_imported(self) -> None:
        from collatz import total_stopping_time
        assert total_stopping_time(27) == 111

    def test_is_power_of_two_imported(self) -> None:
        from collatz import is_power_of_two
        assert is_power_of_two(16)
        assert not is_power_of_two(15)

    def test_get_predecessors_imported(self) -> None:
        from collatz import get_predecessors
        # step(1) = 4, step(8) = 4
        preds = get_predecessors(4)
        assert 8 in preds
        assert 1 in preds

    def test_collatz_error_imported(self) -> None:
        from collatz import CollatzError, step
        with pytest.raises(CollatzError):
            step(-1)

    def test_max_iterations_imported(self) -> None:
        from collatz import MAX_ITERATIONS
        assert isinstance(MAX_ITERATIONS, int)
        assert MAX_ITERATIONS > 0


# ---------------------------------------------------------------------------
# Analysis symbols
# ---------------------------------------------------------------------------

class TestAnalysisExports:
    def test_compute_stats_imported(self) -> None:
        from collatz import compute_stats
        s = compute_stats(27)
        assert s.stopping_time == 111

    def test_trajectory_stats_type(self) -> None:
        from collatz import TrajectoryStats, compute_stats
        s = compute_stats(27)
        assert isinstance(s, TrajectoryStats)

    def test_find_interesting_imported(self) -> None:
        from collatz import find_interesting
        results = find_interesting(1, 20, top_n=3)
        assert len(results) == 3

    def test_glide_imported(self) -> None:
        from collatz import glide
        assert glide(2) == 1

    def test_oscillation_index_imported(self) -> None:
        from collatz import oscillation_index
        v = oscillation_index(27)
        assert 0.0 <= v <= 1.0

    def test_band_persistence_imported(self) -> None:
        from collatz import band_persistence
        v = band_persistence(27)
        assert 0.0 < v <= 1.0

    def test_near_cycle_score_imported(self) -> None:
        from collatz import near_cycle_score
        v = near_cycle_score(27)
        assert 0.0 <= v <= 1.0


# ---------------------------------------------------------------------------
# Version
# ---------------------------------------------------------------------------

class TestVersion:
    def test_version_string_present(self) -> None:
        assert hasattr(collatz, "__version__")
        assert isinstance(collatz.__version__, str)

    def test_version_non_empty(self) -> None:
        assert collatz.__version__.strip() != ""

    def test_version_semver_like(self) -> None:
        parts = collatz.__version__.split(".")
        assert len(parts) >= 2, "Version should be at least MAJOR.MINOR"
        for part in parts:
            assert part.isdigit(), f"Non-numeric version component: {part!r}"


# ---------------------------------------------------------------------------
# Sub-module accessibility
# ---------------------------------------------------------------------------

class TestSubModules:
    def test_core_submodule(self) -> None:
        import collatz.core as core
        assert hasattr(core, "sequence")

    def test_analysis_submodule(self) -> None:
        import collatz.analysis as analysis
        assert hasattr(analysis, "compute_stats")

    def test_visualization_submodule(self) -> None:
        import collatz.visualization as viz
        assert hasattr(viz, "plot_trajectory")

    def test_graph_export_submodule(self) -> None:
        import collatz.graph_export as ge
        assert hasattr(ge, "build_collatz_graph")
        assert hasattr(ge, "build_inverse_tree")
        assert hasattr(ge, "export_csv")
        assert hasattr(ge, "export_image")

    def test_library_submodule(self) -> None:
        import collatz.library as lib
        assert hasattr(lib, "LIBRARY")
