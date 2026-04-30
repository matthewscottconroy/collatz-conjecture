"""
Curated library of mathematically interesting Collatz starting values.

Each entry documents *why* the number is interesting, its category, and
pre-computed key statistics so the GUI can display metadata without running
the full analysis on startup.

Categories
----------
long_trajectory     Numbers holding (near-)records for stopping time.
high_altitude       Numbers whose peak far exceeds their starting value.
heavy_oscillation   Numbers with an unusually high oscillation index.
near_cycle          Numbers that appear to almost cycle for long stretches.
structural          Numbers with noteworthy algebraic structure (powers of 2,
                    Mersenne numbers, etc.) that produce predictable behaviour.
glide_record        Numbers with an unusually long glide before first descent.
visual              Numbers that produce striking visual patterns.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass(frozen=True)
class LibraryEntry:
    """A single entry in the interesting-sequences library.

    Attributes:
        n           : The starting value.
        name        : Short display name.
        description : One or two sentences explaining what makes this n special.
        category    : Primary category string (see module docstring).
        tags        : Additional classification tags.
        stopping_time: Pre-computed total stopping time (steps to reach 1).
        peak_value  : Pre-computed peak value.
        altitude    : Pre-computed altitude (peak / n).
        notes       : Optional longer mathematical note.
    """

    n: int
    name: str
    description: str
    category: str
    tags: tuple[str, ...] = field(default_factory=tuple)
    stopping_time: Optional[int] = None
    peak_value: Optional[int] = None
    altitude: Optional[float] = None
    notes: Optional[str] = None

    def __str__(self) -> str:
        return f"{self.name} (n={self.n:,})"


# ---------------------------------------------------------------------------
# Library entries
# ---------------------------------------------------------------------------

LIBRARY: list[LibraryEntry] = [

    # ------------------------------------------------------------------
    # Category: long_trajectory
    # ------------------------------------------------------------------
    LibraryEntry(
        n=27,
        name="The Celebrity",
        description=(
            "The most famous Collatz starting value. Despite its modest size, "
            "it takes 111 steps to reach 1 — climbing to a peak of 9,232 "
            "(≈342× its start) before finally descending."
        ),
        category="long_trajectory",
        tags=("famous", "high_altitude", "long"),
        stopping_time=111,
        peak_value=9232,
        altitude=341.93,
        notes=(
            "27 is the smallest number requiring more than 100 steps. "
            "It held the record for total stopping time for numbers of its "
            "magnitude for a very long time and remains the canonical example "
            "used in textbooks and lectures."
        ),
    ),
    LibraryEntry(
        n=703,
        name="Triple Digits Champion",
        description=(
            "Requires 170 steps to reach 1, making it one of the longest "
            "trajectories for a 3-digit number, with a peak of 250,504."
        ),
        category="long_trajectory",
        tags=("long", "high_altitude"),
        stopping_time=170,
        peak_value=250504,
        altitude=356.3,
    ),
    LibraryEntry(
        n=871,
        name="The Persistent One",
        description=(
            "Takes 178 steps, slightly beating 703, and climbs to 190,996 "
            "before descending. Notable for sustained high-altitude travel."
        ),
        category="long_trajectory",
        tags=("long",),
        stopping_time=178,
        peak_value=190996,
        altitude=219.3,
    ),
    LibraryEntry(
        n=6171,
        name="Four-Digit Titan",
        description=(
            "261 steps and a peak of 975,400 — almost a thousand times its "
            "starting value. One of the longest trajectories among 4-digit numbers."
        ),
        category="long_trajectory",
        tags=("long", "high_altitude"),
        stopping_time=261,
        peak_value=975400,
        altitude=158.1,
    ),
    LibraryEntry(
        n=77031,
        name="The Long-Haul",
        description=(
            "350 steps and peak at 21,933,016 — one of the most striking "
            "5-digit sequences. The trajectory has several dramatic 'humps' "
            "before the final descent."
        ),
        category="long_trajectory",
        tags=("long", "high_altitude", "multi_hump"),
        stopping_time=350,
        peak_value=21933016,
        altitude=284.8,
    ),
    LibraryEntry(
        n=837799,
        name="Million Milestone",
        description=(
            "Holds the record for longest stopping time among all starting "
            "values below 1,000,000 — 524 steps, peaking at 2,974,984,576."
        ),
        category="long_trajectory",
        tags=("record", "long", "high_altitude"),
        stopping_time=524,
        peak_value=2974984576,
        altitude=3551.0,
        notes=(
            "837,799 was identified by Lempel and others as the below-1M record "
            "holder. Its trajectory is a standard benchmark for Collatz "
            "implementations."
        ),
    ),
    LibraryEntry(
        n=8400511,
        name="Eight-Million Climber",
        description=(
            "685 steps to reach 1 — one of the longest known trajectories "
            "for a number below 10 million."
        ),
        category="long_trajectory",
        tags=("record", "long"),
        stopping_time=685,
        peak_value=None,
        altitude=None,
    ),
    LibraryEntry(
        n=63728127,
        name="Super-Long Trajectory",
        description=(
            "949 steps — among the longest for numbers below 100 million. "
            "The sequence has an extraordinary number of oscillations."
        ),
        category="long_trajectory",
        tags=("record", "long", "heavy_oscillation"),
        stopping_time=949,
        peak_value=None,
        altitude=None,
    ),

    # ------------------------------------------------------------------
    # Category: high_altitude
    # ------------------------------------------------------------------
    LibraryEntry(
        n=9,
        name="First High Flyer",
        description=(
            "Reaches a peak of 52 — about 5.8× its starting value — in just "
            "19 steps. A clean demonstration of the altitude concept."
        ),
        category="high_altitude",
        tags=("small", "educational"),
        stopping_time=19,
        peak_value=52,
        altitude=5.78,
    ),
    LibraryEntry(
        n=703,
        name="Triple Digits Champion",
        description=(
            "Peak/start ratio of ≈356 — one of the highest altitude ratios "
            "for any 3-digit number."
        ),
        category="high_altitude",
        tags=("high_altitude",),
        stopping_time=170,
        peak_value=250504,
        altitude=356.3,
    ),
    LibraryEntry(
        n=9780657631,
        name="Billion-Scale Altitude Record",
        description=(
            "A 10-digit number with an extraordinary altitude: the sequence "
            "climbs many orders of magnitude above its starting value before "
            "collapsing."
        ),
        category="high_altitude",
        tags=("high_altitude", "large"),
        stopping_time=None,
        peak_value=None,
        altitude=None,
    ),

    # ------------------------------------------------------------------
    # Category: heavy_oscillation
    # ------------------------------------------------------------------
    LibraryEntry(
        n=27,
        name="The Celebrity (oscillation view)",
        description=(
            "Besides its length, 27 exhibits repeated heavy oscillation — the "
            "sequence climbs, plunges, climbs again, creating multiple dramatic "
            "humps before finally reaching 1."
        ),
        category="heavy_oscillation",
        tags=("famous", "multi_hump"),
        stopping_time=111,
        peak_value=9232,
        altitude=341.93,
    ),
    LibraryEntry(
        n=447,
        name="Dense Oscillator",
        description=(
            "A 3-digit number with a high proportion of direction reversals "
            "relative to its stopping time — the sequence zigzags intensely."
        ),
        category="heavy_oscillation",
        tags=("oscillation",),
        stopping_time=97,
        peak_value=None,
        altitude=None,
    ),
    LibraryEntry(
        n=3711,
        name="Sustained Zigzag",
        description=(
            "A 4-digit number whose log-scale trajectory has an unusually "
            "large number of local maxima, suggesting persistent up-down "
            "oscillation over most of its length."
        ),
        category="heavy_oscillation",
        tags=("oscillation",),
        stopping_time=237,
        peak_value=None,
        altitude=None,
    ),

    # ------------------------------------------------------------------
    # Category: near_cycle
    # ------------------------------------------------------------------
    LibraryEntry(
        n=27,
        name="The Celebrity (near-cycle view)",
        description=(
            "The sequence from 27 spends an extended period oscillating "
            "within the range [4, 9232] before descending — suggesting "
            "quasi-cyclic behaviour."
        ),
        category="near_cycle",
        tags=("famous",),
        stopping_time=111,
        peak_value=9232,
        altitude=341.93,
    ),
    LibraryEntry(
        n=231,
        name="Band Dweller",
        description=(
            "After an initial climb the sequence from 231 spends a long "
            "stretch oscillating within a narrow band before the final "
            "descent, scoring highly on the band-persistence metric."
        ),
        category="near_cycle",
        tags=("band_persistence",),
        stopping_time=127,
        peak_value=None,
        altitude=None,
    ),
    LibraryEntry(
        n=6943,
        name="Persistent Band Oscillator",
        description=(
            "Spends an unusually long contiguous stretch within a 4× value "
            "window — one of the stronger near-cycle candidates below 10,000."
        ),
        category="near_cycle",
        tags=("band_persistence",),
        stopping_time=None,
        peak_value=None,
        altitude=None,
    ),

    # ------------------------------------------------------------------
    # Category: structural
    # ------------------------------------------------------------------
    LibraryEntry(
        n=2,
        name="Simplest Power of Two",
        description=(
            "2 → 1 in a single step. All powers of two collapse immediately: "
            "2^k takes exactly k steps."
        ),
        category="structural",
        tags=("power_of_two", "educational"),
        stopping_time=1,
        peak_value=2,
        altitude=1.0,
    ),
    LibraryEntry(
        n=4,
        name="Trivial Cycle Start",
        description=(
            "The number 4 is part of the only known positive-integer cycle: "
            "4 → 2 → 1 → 4 → ... The conjecture claims this is the unique cycle."
        ),
        category="structural",
        tags=("cycle", "educational"),
        stopping_time=2,
        peak_value=4,
        altitude=1.0,
        notes=(
            "The Collatz conjecture is equivalent to: the only positive-integer "
            "cycle of the 3x+1 map is {1, 2, 4}."
        ),
    ),
    LibraryEntry(
        n=1024,
        name="2^10",
        description=(
            "A power of two: takes exactly 10 steps (one halving per step). "
            "Perfect for testing that an implementation handles even-only paths."
        ),
        category="structural",
        tags=("power_of_two", "educational"),
        stopping_time=10,
        peak_value=1024,
        altitude=1.0,
    ),
    LibraryEntry(
        n=65535,
        name="Mersenne-like: 2^16 − 1",
        description=(
            "Numbers of the form 2^k − 1 are odd and trigger 3n+1 immediately, "
            "starting every step with an upward jump. 65535 produces a long "
            "and complex sequence."
        ),
        category="structural",
        tags=("mersenne_like", "odd_start"),
        stopping_time=None,
        peak_value=None,
        altitude=None,
        notes=(
            "True Mersenne numbers are 2^p − 1 for prime p. Numbers of this "
            "form are of interest because they maximise the first step of the "
            "sequence."
        ),
    ),
    LibraryEntry(
        n=3,
        name="Smallest Non-Trivial Odd",
        description=(
            "3 → 10 → 5 → 16 → 8 → 4 → 2 → 1. Just 7 steps. "
            "Shows the classic up-down-up-down pattern in miniature."
        ),
        category="structural",
        tags=("small", "educational"),
        stopping_time=7,
        peak_value=16,
        altitude=5.33,
    ),

    # ------------------------------------------------------------------
    # Category: glide_record
    # ------------------------------------------------------------------
    LibraryEntry(
        n=871,
        name="Long Glide",
        description=(
            "The sequence from 871 resists dropping below 871 for an "
            "unusually large number of steps — a record 'glide' for its size."
        ),
        category="glide_record",
        tags=("glide",),
        stopping_time=178,
        peak_value=190996,
        altitude=219.3,
    ),
    LibraryEntry(
        n=77031,
        name="Extended Glide",
        description=(
            "Also notable for glide: 77031 does not fall below its starting "
            "value until very late in its 350-step trajectory."
        ),
        category="glide_record",
        tags=("glide", "long"),
        stopping_time=350,
        peak_value=21933016,
        altitude=284.8,
    ),

    # ------------------------------------------------------------------
    # Category: visual
    # ------------------------------------------------------------------
    LibraryEntry(
        n=27,
        name="The Celebrity (visual)",
        description=(
            "Produces the most visually striking single-sequence plot: a "
            "dramatic spike to 9,232 followed by a jagged multi-stage descent."
        ),
        category="visual",
        tags=("famous", "spike"),
        stopping_time=111,
        peak_value=9232,
        altitude=341.93,
    ),
    LibraryEntry(
        n=100,
        name="Round Hundred",
        description=(
            "A clean, easy-to-inspect trajectory (25 steps) often used in "
            "demonstrations. The log-scale view reveals its structure clearly."
        ),
        category="visual",
        tags=("educational", "clean"),
        stopping_time=25,
        peak_value=100,
        altitude=1.0,
    ),
    LibraryEntry(
        n=341,
        name="Phase Portrait Star",
        description=(
            "When plotted as a phase portrait (n_k vs n_{k+1}) the sequence "
            "from 341 traces an unusually symmetric and visually interesting "
            "path."
        ),
        category="visual",
        tags=("phase_portrait",),
        stopping_time=None,
        peak_value=None,
        altitude=None,
    ),
]


# ---------------------------------------------------------------------------
# Accessors
# ---------------------------------------------------------------------------

def all_entries() -> list[LibraryEntry]:
    """Return all library entries."""
    return list(LIBRARY)


def by_category(category: str) -> list[LibraryEntry]:
    """Return all entries whose primary category matches *category*.

    Args:
        category: e.g. 'long_trajectory', 'high_altitude', etc.

    Returns:
        Possibly-empty list of matching entries.
    """
    return [e for e in LIBRARY if e.category == category]


def by_tag(tag: str) -> list[LibraryEntry]:
    """Return all entries that carry *tag*.

    Args:
        tag: e.g. 'famous', 'record', 'educational'.

    Returns:
        Possibly-empty list of matching entries.
    """
    return [e for e in LIBRARY if tag in e.tags]


def categories() -> list[str]:
    """Return the sorted list of distinct categories present in the library."""
    return sorted({e.category for e in LIBRARY})


def find_entry(n: int) -> list[LibraryEntry]:
    """Return all library entries whose starting value is n.

    A single n can appear in multiple categories.

    Args:
        n: Starting value to look up.

    Returns:
        List of matching entries (may be empty).
    """
    return [e for e in LIBRARY if e.n == n]


CATEGORY_LABELS: dict[str, str] = {
    "long_trajectory": "Long Trajectories",
    "high_altitude": "High Altitude",
    "heavy_oscillation": "Heavy Oscillation",
    "near_cycle": "Near-Cycle Behaviour",
    "structural": "Structural / Mathematical",
    "glide_record": "Glide Records",
    "visual": "Visually Interesting",
}
