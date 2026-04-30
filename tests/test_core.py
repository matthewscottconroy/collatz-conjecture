"""
Tests for collatz.core — step, sequence, sequence_iter, total_stopping_time,
is_power_of_two, and CollatzError behaviour.
"""

import pytest

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


# ---------------------------------------------------------------------------
# step()
# ---------------------------------------------------------------------------

class TestStep:
    def test_even_number_halved(self) -> None:
        assert step(10) == 5
        assert step(8) == 4
        assert step(2) == 1

    def test_odd_number_triple_plus_one(self) -> None:
        assert step(1) == 4   # 3*1+1
        assert step(3) == 10  # 3*3+1
        assert step(5) == 16  # 3*5+1
        assert step(7) == 22  # 3*7+1

    def test_large_even(self) -> None:
        n = 1_000_000
        assert step(n) == 500_000

    def test_large_odd(self) -> None:
        n = 999_999
        assert step(n) == 3 * 999_999 + 1

    def test_raises_on_zero(self) -> None:
        with pytest.raises(CollatzError):
            step(0)

    def test_raises_on_negative(self) -> None:
        with pytest.raises(CollatzError):
            step(-1)

    def test_raises_on_float(self) -> None:
        with pytest.raises(CollatzError):
            step(3.0)  # type: ignore[arg-type]

    def test_raises_on_string(self) -> None:
        with pytest.raises(CollatzError):
            step("5")  # type: ignore[arg-type]

    def test_step_one(self) -> None:
        # 1 is odd: 3*1+1 = 4
        assert step(1) == 4


# ---------------------------------------------------------------------------
# sequence()
# ---------------------------------------------------------------------------

class TestSequence:
    def test_trivial_cycle_members(self) -> None:
        # 1 → [1]
        assert sequence(1) == [1]
        # 2 → [2, 1]
        assert sequence(2) == [2, 1]
        # 4 → [4, 2, 1]
        assert sequence(4) == [4, 2, 1]

    def test_three(self) -> None:
        assert sequence(3) == [3, 10, 5, 16, 8, 4, 2, 1]

    def test_starts_with_n(self) -> None:
        for n in [1, 7, 27, 100]:
            assert sequence(n)[0] == n

    def test_ends_with_one(self) -> None:
        for n in [1, 6, 27, 1000]:
            assert sequence(n)[-1] == 1

    def test_consecutive_steps_valid(self) -> None:
        seq = sequence(27)
        for i in range(len(seq) - 1):
            assert seq[i + 1] == step(seq[i])

    def test_known_length_n27(self) -> None:
        # 27 takes 111 steps → 112 elements.
        assert len(sequence(27)) == 112

    def test_known_peak_n27(self) -> None:
        assert max(sequence(27)) == 9232

    def test_raises_on_non_positive(self) -> None:
        with pytest.raises(CollatzError):
            sequence(0)
        with pytest.raises(CollatzError):
            sequence(-5)

    def test_power_of_two_length(self) -> None:
        # 2^k has exactly k+1 elements: [2^k, 2^(k-1), ..., 2, 1]
        for k in range(1, 15):
            assert len(sequence(2 ** k)) == k + 1

    def test_sequence_contains_no_zero(self) -> None:
        for n in [1, 3, 27, 100]:
            assert 0 not in sequence(n)


# ---------------------------------------------------------------------------
# sequence_iter()
# ---------------------------------------------------------------------------

class TestSequenceIter:
    def test_produces_same_as_sequence(self) -> None:
        for n in [1, 3, 10, 27, 100]:
            assert list(sequence_iter(n)) == sequence(n)

    def test_raises_on_non_positive(self) -> None:
        with pytest.raises(CollatzError):
            list(sequence_iter(0))

    def test_is_generator(self) -> None:
        import types
        gen = sequence_iter(10)
        assert isinstance(gen, types.GeneratorType)

    def test_first_yield_is_n(self) -> None:
        gen = sequence_iter(42)
        assert next(gen) == 42

    def test_last_yield_is_one(self) -> None:
        result = list(sequence_iter(17))
        assert result[-1] == 1


# ---------------------------------------------------------------------------
# total_stopping_time()
# ---------------------------------------------------------------------------

class TestTotalStoppingTime:
    def test_one_is_zero(self) -> None:
        assert total_stopping_time(1) == 0

    def test_two_is_one(self) -> None:
        assert total_stopping_time(2) == 1

    def test_known_values(self) -> None:
        known = {
            1: 0,
            2: 1,
            3: 7,
            4: 2,
            5: 5,
            6: 8,
            7: 16,
            8: 3,
            9: 19,
            10: 6,
            27: 111,
        }
        for n, expected in known.items():
            assert total_stopping_time(n) == expected, (
                f"total_stopping_time({n}) expected {expected}"
            )

    def test_power_of_two(self) -> None:
        for k in range(1, 20):
            assert total_stopping_time(2 ** k) == k

    def test_equals_sequence_length_minus_one(self) -> None:
        for n in [1, 3, 27, 100, 1000]:
            assert total_stopping_time(n) == len(sequence(n)) - 1

    def test_raises_on_non_positive(self) -> None:
        with pytest.raises(CollatzError):
            total_stopping_time(0)

    def test_no_recursion_error_for_long_sequence(self) -> None:
        # n=63_728_127 has a stopping time of ~949 steps.  The previous
        # recursive implementation would raise RecursionError because Python's
        # default recursion limit (~1000) was exceeded.
        result = total_stopping_time(63_728_127)
        assert result > 900
        assert result == len(sequence(63_728_127)) - 1

    def test_memoisation_returns_same_result(self) -> None:
        # Calling twice must return the same value (cache hit path).
        assert total_stopping_time(500) == total_stopping_time(500)

    def test_intermediate_values_cached(self) -> None:
        # After computing n=27 the intermediate values are cached;
        # computing a value that lies on 27's path should be fast and correct.
        total_stopping_time(27)  # primes the cache
        # 10 is on the path of 27 and has stopping time 6.
        assert total_stopping_time(10) == 6


class TestSequenceMaxIterBoundary:
    """Verify the off-by-one fix: max_iter means exactly max_iter steps allowed."""

    def test_exact_steps_succeeds(self) -> None:
        # n=3 has 7 steps; sequence(3, max_iter=7) must succeed.
        exact = total_stopping_time(3)  # == 7
        result = sequence(3, max_iter=exact)
        assert result[-1] == 1
        assert len(result) == exact + 1

    def test_one_fewer_raises(self) -> None:
        # Allowing one fewer step than needed must raise.
        exact = total_stopping_time(3)
        with pytest.raises(CollatzError):
            sequence(3, max_iter=exact - 1)

    def test_one_more_succeeds(self) -> None:
        exact = total_stopping_time(3)
        result = sequence(3, max_iter=exact + 1)
        assert result[-1] == 1


# ---------------------------------------------------------------------------
# is_power_of_two()
# ---------------------------------------------------------------------------

class TestIsPowerOfTwo:
    def test_powers(self) -> None:
        for k in range(0, 30):
            assert is_power_of_two(2 ** k)

    def test_non_powers(self) -> None:
        for n in [3, 5, 6, 7, 9, 10, 12, 15, 100, 1000]:
            assert not is_power_of_two(n)

    def test_raises_on_non_positive(self) -> None:
        with pytest.raises(CollatzError):
            is_power_of_two(0)
        with pytest.raises(CollatzError):
            is_power_of_two(-1)

    def test_one_is_power_of_two(self) -> None:
        # 1 = 2^0
        assert is_power_of_two(1)


# ---------------------------------------------------------------------------
# get_predecessors()
# ---------------------------------------------------------------------------

class TestGetPredecessors:
    def test_even_predecessor_always_present(self) -> None:
        for n in [1, 2, 3, 4, 10, 27, 100]:
            assert 2 * n in get_predecessors(n)

    def test_step_of_each_predecessor_equals_n(self) -> None:
        for n in range(1, 60):
            for pred in get_predecessors(n):
                assert step(pred) == n, (
                    f"step({pred}) should equal {n}, got {step(pred)}"
                )

    def test_n4_has_odd_predecessor_1(self) -> None:
        # step(1) = 4, so 1 is the odd predecessor of 4.
        assert 1 in get_predecessors(4)

    def test_n16_has_odd_predecessor_5(self) -> None:
        assert 5 in get_predecessors(16)

    def test_n10_has_odd_predecessor_3(self) -> None:
        assert 3 in get_predecessors(10)

    def test_n2_has_only_even_predecessor(self) -> None:
        # (2-1)/3 = 1/3 is not an integer.
        assert get_predecessors(2) == [4]

    def test_n3_has_only_even_predecessor(self) -> None:
        # (3-1)/3 = 2/3 is not an integer.
        assert get_predecessors(3) == [6]

    def test_raises_on_non_positive(self) -> None:
        with pytest.raises(CollatzError):
            get_predecessors(0)
        with pytest.raises(CollatzError):
            get_predecessors(-5)

    def test_at_most_two_predecessors(self) -> None:
        for n in range(1, 100):
            assert len(get_predecessors(n)) <= 2


# ---------------------------------------------------------------------------
# CollatzError
# ---------------------------------------------------------------------------

class TestCollatzError:
    def test_is_value_error_subclass(self) -> None:
        assert issubclass(CollatzError, ValueError)

    def test_error_message_contains_input(self) -> None:
        try:
            step(-42)
        except CollatzError as exc:
            assert "-42" in str(exc)


# ---------------------------------------------------------------------------
# Edge cases and cross-function consistency
# ---------------------------------------------------------------------------

class TestEdgeCases:
    """Cross-function and boundary-value consistency checks."""

    def test_sequence_length_equals_stopping_time_plus_one(self) -> None:
        for n in [1, 2, 3, 6, 27, 100, 1000]:
            assert len(sequence(n)) == total_stopping_time(n) + 1

    def test_step_matches_sequence_transitions(self) -> None:
        seq = sequence(100)
        for i in range(len(seq) - 1):
            assert step(seq[i]) == seq[i + 1]

    def test_all_sequence_values_positive(self) -> None:
        for n in [1, 7, 27, 255]:
            assert all(v > 0 for v in sequence(n))

    def test_sequence_iter_matches_sequence_for_edge_values(self) -> None:
        for n in [1, 2, 16, 27]:
            assert list(sequence_iter(n)) == sequence(n)

    def test_is_power_of_two_and_sequence_length(self) -> None:
        # 2**k has exactly k+1 elements and total_stopping_time == k.
        for k in range(1, 16):
            n = 2 ** k
            assert is_power_of_two(n)
            assert total_stopping_time(n) == k
            assert len(sequence(n)) == k + 1

    def test_get_predecessors_round_trip(self) -> None:
        # step(pred) must equal n for every predecessor returned.
        for n in range(1, 50):
            for pred in get_predecessors(n):
                assert step(pred) == n

    def test_sequence_n_power_of_two_monotone_decreasing(self) -> None:
        for k in range(1, 10):
            seq = sequence(2 ** k)
            for i in range(len(seq) - 1):
                assert seq[i] > seq[i + 1]

    def test_stopping_time_cache_consistency(self) -> None:
        # Computing stopping times in different orders must give the same value.
        forward = [total_stopping_time(n) for n in range(1, 100)]
        backward = [total_stopping_time(n) for n in range(99, 0, -1)]
        assert forward == list(reversed(backward))
