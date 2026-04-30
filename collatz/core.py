"""
Core Collatz sequence computation.

The Collatz function is defined for positive integers n as:
    f(n) = n / 2       if n is even
    f(n) = 3 * n + 1   if n is odd

The conjecture states that for any positive integer n, repeated application
of f eventually reaches 1, entering the trivial cycle 1 → 4 → 2 → 1.
"""

from __future__ import annotations

from typing import Generator


MAX_ITERATIONS: int = 10_000_000

# Memoisation table for total_stopping_time.  Pre-seeded with the base case.
_tst_cache: dict[int, int] = {1: 0}


class CollatzError(ValueError):
    """Raised when an invalid input is provided to a Collatz function."""


# ---------------------------------------------------------------------------
# Internal hot-path helper (no input validation)
# ---------------------------------------------------------------------------

def _step(n: int) -> int:
    """Apply one Collatz step without input validation.

    Used internally in tight loops where the caller guarantees n > 0.
    """
    if n % 2 == 0:
        return n >> 1
    return 3 * n + 1


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def step(n: int) -> int:
    """Apply a single Collatz step to n.

    Args:
        n: A positive integer.

    Returns:
        n // 2 if n is even, else 3 * n + 1.

    Raises:
        CollatzError: If n is not a positive integer.
    """
    if not isinstance(n, int) or n <= 0:
        raise CollatzError(f"Input must be a positive integer, got {n!r}")
    return _step(n)


def sequence(n: int, max_iter: int = MAX_ITERATIONS) -> list[int]:
    """Compute the full Collatz sequence from n down to 1.

    Args:
        n: Starting positive integer.
        max_iter: Maximum number of steps allowed.  Raises CollatzError if
            the sequence has not reached 1 after this many steps.

    Returns:
        A list starting with n and ending with 1, e.g. [27, 82, 41, ...].
        The list has exactly (stopping_time + 1) elements.

    Raises:
        CollatzError: If n <= 0 or the sequence exceeds max_iter steps.
    """
    if not isinstance(n, int) or n <= 0:
        raise CollatzError(f"Input must be a positive integer, got {n!r}")
    result = [n]
    current = n
    while current != 1:
        if len(result) > max_iter:
            raise CollatzError(
                f"Sequence from {n} did not terminate within {max_iter} steps"
            )
        current = _step(current)
        result.append(current)
    return result


def sequence_iter(n: int) -> Generator[int, None, None]:
    """Yield Collatz sequence values one at a time, starting at n ending at 1.

    Memory-efficient alternative to sequence() for very long trajectories.

    Args:
        n: Starting positive integer.

    Yields:
        Successive values of the Collatz sequence.

    Raises:
        CollatzError: If n <= 0 or the sequence exceeds MAX_ITERATIONS steps.
    """
    if not isinstance(n, int) or n <= 0:
        raise CollatzError(f"Input must be a positive integer, got {n!r}")
    yield n
    steps = 0
    while n != 1:
        if steps >= MAX_ITERATIONS:
            raise CollatzError(
                f"Sequence did not terminate within {MAX_ITERATIONS} steps"
            )
        n = _step(n)
        steps += 1
        yield n


def total_stopping_time(n: int) -> int:
    """Return the number of steps for the sequence from n to reach 1.

    Uses an iterative algorithm with a shared memoisation table.  Looking up
    any previously-computed value is O(1); computing a new value fills the
    cache for every intermediate point along the path, amortising future calls.

    This implementation avoids Python's recursion limit, which the previous
    recursive version would exceed for inputs with stopping times above ~997
    (e.g. n = 63_728_127 which has 949 steps).

    Args:
        n: Starting positive integer.

    Returns:
        Number of Collatz steps from n to 1.

    Raises:
        CollatzError: If n <= 0.
    """
    if not isinstance(n, int) or n <= 0:
        raise CollatzError(f"Input must be a positive integer, got {n!r}")
    if n in _tst_cache:
        return _tst_cache[n]

    # Walk forward until we hit a cached value, recording the path.
    path: list[int] = []
    current = n
    while current not in _tst_cache:
        if len(path) >= MAX_ITERATIONS:
            raise CollatzError(
                f"Sequence from {n} did not terminate within {MAX_ITERATIONS} steps"
            )
        path.append(current)
        current = _step(current)

    # Fill the cache backwards from the known base.
    base = _tst_cache[current]
    for dist, val in enumerate(reversed(path), start=1):
        _tst_cache[val] = base + dist

    return _tst_cache[n]


def get_predecessors(n: int) -> list[int]:
    """Return the direct predecessors of n under the Collatz map.

    Every positive integer n has exactly one *even predecessor*: 2n, because
    step(2n) = 2n // 2 = n.  It may also have one *odd predecessor* m with
    step(m) = 3m + 1 = n, which requires n ≡ 1 (mod 3) and m = (n-1)//3 to
    be a positive odd integer.

    Args:
        n: A positive integer.

    Returns:
        List of length 1 or 2.  The even predecessor 2n is always first; the
        odd predecessor (n-1)//3 appears second when it exists.

    Raises:
        CollatzError: If n is not a positive integer.
    """
    if not isinstance(n, int) or n <= 0:
        raise CollatzError(f"Input must be a positive integer, got {n!r}")
    result = [2 * n]
    if n > 1 and (n - 1) % 3 == 0:
        m = (n - 1) // 3
        if m >= 1 and m % 2 == 1:   # m must be odd (even m is covered by even branch)
            result.append(m)
    return result


def is_power_of_two(n: int) -> bool:
    """Return True if n is a power of two (including 1 = 2**0).

    Powers of two collapse immediately: each step halves n.

    Args:
        n: A positive integer.

    Returns:
        True iff n == 2**k for some non-negative integer k.
    """
    if not isinstance(n, int) or n <= 0:
        raise CollatzError(f"Input must be a positive integer, got {n!r}")
    return (n & (n - 1)) == 0
