"""
Tests for collatz.analysis — TrajectoryStats, metric functions, and
find_interesting range scanner.
"""

import math

import pytest

from collatz.analysis import (
    TrajectoryStats,
    _compute_band_persistence,
    _compute_glide,
    _compute_near_cycle_score,
    _compute_oscillation_index,
    band_persistence,
    compute_stats,
    find_interesting,
    glide,
    near_cycle_score,
    oscillation_index,
)
from collatz.core import sequence


# ---------------------------------------------------------------------------
# Helper: build a fake constant sequence for isolated testing
# ---------------------------------------------------------------------------

def _flat_seq(n: int, length: int) -> list[int]:
    """Returns [n, n, n, ..., 1] with 'length' copies of n then 1."""
    return [n] * length + [1]


# ---------------------------------------------------------------------------
# TrajectoryStats
# ---------------------------------------------------------------------------

class TestTrajectoryStats:
    def _stats(self, n: int) -> TrajectoryStats:
        return compute_stats(n)

    def test_n_stored(self) -> None:
        assert self._stats(27).n == 27

    def test_seq_starts_with_n(self) -> None:
        assert self._stats(27).seq[0] == 27

    def test_seq_ends_with_one(self) -> None:
        assert self._stats(27).seq[-1] == 1

    def test_length_equals_seq_length(self) -> None:
        s = self._stats(100)
        assert s.length == len(s.seq)

    def test_stopping_time_correct(self) -> None:
        s = self._stats(27)
        assert s.stopping_time == 111

    def test_peak_value_n27(self) -> None:
        s = self._stats(27)
        assert s.peak_value == 9232

    def test_altitude_n27(self) -> None:
        s = self._stats(27)
        assert abs(s.altitude - 9232 / 27) < 0.01

    def test_even_plus_odd_equals_stopping_time(self) -> None:
        s = self._stats(27)
        assert s.even_steps + s.odd_steps == s.stopping_time

    def test_odd_fraction_in_range(self) -> None:
        s = self._stats(27)
        assert 0.0 <= s.odd_fraction <= 1.0

    def test_oscillation_in_range(self) -> None:
        for n in [1, 3, 27, 100]:
            s = self._stats(n)
            assert 0.0 <= s.oscillation_index <= 1.0

    def test_band_persistence_in_range(self) -> None:
        for n in [1, 3, 27, 100]:
            s = self._stats(n)
            assert 0.0 < s.band_persistence <= 1.0

    def test_near_cycle_score_in_range(self) -> None:
        for n in [3, 27, 100, 1000]:
            s = self._stats(n)
            assert 0.0 <= s.near_cycle_score <= 1.0

    def test_n1_has_zero_stopping_time(self) -> None:
        s = self._stats(1)
        assert s.stopping_time == 0
        assert s.odd_steps == 0
        assert s.even_steps == 0

    def test_summary_contains_n(self) -> None:
        s = self._stats(27)
        assert "27" in s.summary()


# ---------------------------------------------------------------------------
# glide()
# ---------------------------------------------------------------------------

class TestGlide:
    def test_n1(self) -> None:
        # Sequence is [1]; never drops below 1 before reaching 1.
        assert glide(1) == 0

    def test_n2(self) -> None:
        # [2, 1]: first step drops below 2.
        assert glide(2) == 1

    def test_n4(self) -> None:
        # [4, 2, 1]: step 1 reaches 2 < 4.
        assert glide(4) == 1

    def test_n3(self) -> None:
        # [3, 10, 5, 16, 8, 4, 2, 1]
        # 10 > 3, 5 > 3, 16 > 3, 8 > 3, 4 > 3, 2 < 3  → glide = 6
        assert glide(3) == 6

    def test_positive_for_all_nontrivial(self) -> None:
        for n in range(2, 50):
            assert glide(n) >= 1

    def test_glide_less_than_stopping_time(self) -> None:
        for n in range(2, 100):
            from collatz.core import total_stopping_time
            assert glide(n) <= total_stopping_time(n)


# ---------------------------------------------------------------------------
# oscillation_index()
# ---------------------------------------------------------------------------

class TestOscillationIndex:
    def test_monotone_decreasing_is_zero(self) -> None:
        # All powers of 2: [2^k, 2^(k-1), ..., 1] — strictly decreasing.
        for k in range(2, 12):
            assert oscillation_index(2 ** k) == 0.0

    def test_range_constraint(self) -> None:
        for n in range(1, 100):
            v = oscillation_index(n)
            assert 0.0 <= v <= 1.0

    def test_n3_has_oscillations(self) -> None:
        # [3, 10, 5, 16, 8, 4, 2, 1] — local maxima at 10 and 16.
        v = oscillation_index(3)
        assert v > 0.0

    def test_n1_is_zero(self) -> None:
        assert oscillation_index(1) == 0.0

    def test_computed_manually_n3(self) -> None:
        seq = [3, 10, 5, 16, 8, 4, 2, 1]
        # Interior = [10, 5, 16, 8, 4, 2]
        # Local maxima: 10 (10>3, 10>5) yes; 5 no; 16 (16>5, 16>8) yes; 8 no; 4 no; 2 no
        # count = 2, len(interior) = 6
        assert abs(_compute_oscillation_index(seq) - 2 / 6) < 1e-9


# ---------------------------------------------------------------------------
# band_persistence()
# ---------------------------------------------------------------------------

class TestBandPersistence:
    def test_constant_sequence_is_one(self) -> None:
        # All identical values: max/min == 1 ≤ bandwidth_ratio, so entire window fits.
        seq = [5, 5, 5, 5, 5]
        assert abs(_compute_band_persistence(seq, bandwidth_ratio=1.0) - 1.0) < 1e-9

    def test_empty_sequence(self) -> None:
        assert _compute_band_persistence([]) == 0.0

    def test_single_element(self) -> None:
        assert _compute_band_persistence([42]) == 1.0

    def test_monotone_powers_of_two(self) -> None:
        seq = [16, 8, 4, 2, 1]
        # Bandwidth ratio 2: best window is any pair [2k, k] → length 2, fraction 0.4
        assert abs(_compute_band_persistence(seq, bandwidth_ratio=2.0) - 2 / 5) < 1e-9

    def test_in_range(self) -> None:
        for n in range(1, 50):
            v = band_persistence(n)
            assert 0.0 < v <= 1.0

    def test_high_bandwidth_always_full(self) -> None:
        # With a huge bandwidth ratio, the whole sequence fits.
        seq = sequence(27)
        assert abs(_compute_band_persistence(seq, bandwidth_ratio=1e18) - 1.0) < 1e-9


# ---------------------------------------------------------------------------
# near_cycle_score()
# ---------------------------------------------------------------------------

class TestNearCycleScore:
    def test_range_constraint(self) -> None:
        for n in [3, 7, 27, 100, 1000]:
            v = near_cycle_score(n)
            assert 0.0 <= v <= 1.0

    def test_constant_maxima_is_one(self) -> None:
        # Hand-craft a sequence with identical local maxima.
        # [1, 5, 1, 5, 1] — maxima at positions 1 and 3, both value 5.
        seq = [1, 5, 1, 5, 1]
        score = _compute_near_cycle_score(seq)
        assert abs(score - 1.0) < 1e-9

    def test_short_seq_no_maxima(self) -> None:
        # Monotone sequence → no local maxima → score 0.
        assert _compute_near_cycle_score([10, 5, 2, 1]) == 0.0

    def test_two_maxima_different(self) -> None:
        # [1, 10, 1, 100, 1]
        seq = [1, 10, 1, 100, 1]
        score = _compute_near_cycle_score(seq)
        # CV should be high → score well below 1.
        assert score < 0.9

    def test_n1(self) -> None:
        # [1] — no interior → 0.
        assert near_cycle_score(1) == 0.0


# ---------------------------------------------------------------------------
# compute_stats() integration
# ---------------------------------------------------------------------------

class TestComputeStats:
    def test_n27_full(self) -> None:
        s = compute_stats(27)
        assert s.stopping_time == 111
        assert s.peak_value == 9232
        assert abs(s.altitude - 9232 / 27) < 0.01
        assert 0 <= s.oscillation_index <= 1
        assert s.even_steps + s.odd_steps == 111

    def test_n1(self) -> None:
        s = compute_stats(1)
        assert s.stopping_time == 0
        assert s.peak_value == 1
        assert s.altitude == 1.0

    def test_power_of_two(self) -> None:
        s = compute_stats(64)
        assert s.stopping_time == 6
        assert s.peak_value == 64
        assert s.altitude == 1.0
        assert s.oscillation_index == 0.0  # strictly decreasing


# ---------------------------------------------------------------------------
# find_interesting()
# ---------------------------------------------------------------------------

class TestFindInteresting:
    def test_returns_top_n(self) -> None:
        results = find_interesting(1, 50, top_n=5)
        assert len(results) == 5

    def test_sorted_descending(self) -> None:
        results = find_interesting(1, 100, metric="stopping_time", top_n=10)
        scores = [s for _, s in results]
        assert scores == sorted(scores, reverse=True)

    def test_known_winner_stopping_time(self) -> None:
        # 97 has the longest stopping time (118 steps) of all n in [1, 100].
        results = find_interesting(1, 100, metric="stopping_time", top_n=1)
        assert results[0][0] == 97

    def test_altitude_metric(self) -> None:
        results = find_interesting(1, 100, metric="altitude", top_n=5)
        assert len(results) == 5
        for n, score in results:
            assert score > 0

    def test_all_metrics_work(self) -> None:
        metrics = ["stopping_time", "altitude", "oscillation_index",
                   "band_persistence", "near_cycle_score"]
        for m in metrics:
            results = find_interesting(1, 30, metric=m, top_n=3)
            assert len(results) == 3

    def test_top_n_larger_than_range_returns_all(self) -> None:
        # Range [5, 7] has only 3 values; top_n=100 should return all 3.
        results = find_interesting(5, 7, top_n=100)
        assert len(results) == 3
        assert {n for n, _ in results} == {5, 6, 7}

    def test_invalid_start_raises(self) -> None:
        with pytest.raises(ValueError):
            find_interesting(0, 10)

    def test_start_greater_than_end_raises(self) -> None:
        with pytest.raises(ValueError):
            find_interesting(50, 10)

    def test_unknown_metric_raises(self) -> None:
        with pytest.raises(ValueError):
            find_interesting(1, 10, metric="unknown_metric")

    def test_single_value_range(self) -> None:
        results = find_interesting(27, 27, top_n=5)
        assert len(results) == 1
        assert results[0][0] == 27


# ---------------------------------------------------------------------------
# TrajectoryStats edge cases
# ---------------------------------------------------------------------------

class TestTrajectoryStatsEdgeCases:
    def test_n2_stopping_time(self) -> None:
        s = compute_stats(2)
        assert s.stopping_time == 1
        assert s.peak_value == 2
        assert s.altitude == 1.0

    def test_n2_odd_and_even_steps(self) -> None:
        # seq=[2,1]: one even step, zero odd steps.
        s = compute_stats(2)
        assert s.even_steps == 1
        assert s.odd_steps == 0
        assert s.odd_fraction == 0.0

    def test_summary_format_all_fields(self) -> None:
        s = compute_stats(27)
        text = s.summary()
        for label in [
            "Stopping time", "Peak value", "Altitude", "Glide",
            "Oscillation", "Band persistence", "Near-cycle", "Odd steps", "Even steps",
        ]:
            assert label in text, f"Summary missing label: {label!r}"

    def test_precomputed_seq_gives_same_stats(self) -> None:
        from collatz.core import sequence
        seq = sequence(100)
        s1 = compute_stats(100)
        s2 = compute_stats(100, seq=seq)
        assert s1.stopping_time == s2.stopping_time
        assert s1.peak_value == s2.peak_value
        assert abs(s1.altitude - s2.altitude) < 1e-10

    def test_power_of_two_zero_odd_steps(self) -> None:
        # All steps in a power-of-two sequence are even halvings.
        s = compute_stats(32)
        assert s.odd_steps == 0
        assert s.even_steps == s.stopping_time

    def test_odd_fraction_plus_even_fraction_is_one(self) -> None:
        for n in [3, 27, 100]:
            s = compute_stats(n)
            if s.stopping_time > 0:
                even_frac = s.even_steps / s.stopping_time
                assert abs(s.odd_fraction + even_frac - 1.0) < 1e-10


# ---------------------------------------------------------------------------
# find_interesting() additional edge cases
# ---------------------------------------------------------------------------

class TestFindInterestingEdgeCases:
    def test_oscillation_index_metric(self) -> None:
        results = find_interesting(1, 50, metric="oscillation_index", top_n=5)
        assert len(results) == 5
        scores = [s for _, s in results]
        assert scores == sorted(scores, reverse=True)

    def test_band_persistence_metric(self) -> None:
        results = find_interesting(1, 50, metric="band_persistence", top_n=5)
        assert len(results) == 5

    def test_near_cycle_score_metric(self) -> None:
        results = find_interesting(1, 50, metric="near_cycle_score", top_n=5)
        assert len(results) == 5

    def test_results_are_tuples_of_int_float(self) -> None:
        results = find_interesting(1, 20)
        for n, score in results:
            assert isinstance(n, int)
            assert isinstance(score, float)


# ---------------------------------------------------------------------------
# find_interesting() progress callback
# ---------------------------------------------------------------------------

class TestFindInterestingProgress:
    def test_callback_called_for_each_value(self) -> None:
        calls: list[tuple[int, int]] = []
        find_interesting(1, 10, progress=lambda d, t: calls.append((d, t)))
        assert len(calls) == 10

    def test_callback_receives_correct_total(self) -> None:
        totals: list[int] = []
        find_interesting(5, 14, progress=lambda d, t: totals.append(t))
        assert all(t == 10 for t in totals)

    def test_callback_done_increments_from_one(self) -> None:
        dones: list[int] = []
        find_interesting(1, 5, progress=lambda d, t: dones.append(d))
        assert dones == [1, 2, 3, 4, 5]

    def test_no_callback_works_fine(self) -> None:
        results = find_interesting(1, 10)
        assert len(results) == 10

    def test_callback_not_called_on_empty_compatible_range(self) -> None:
        calls: list = []
        find_interesting(7, 7, progress=lambda d, t: calls.append((d, t)))
        assert len(calls) == 1
        assert calls[0] == (1, 1)
