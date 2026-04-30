"""
Tests for collatz.library — LibraryEntry structure, accessor functions,
and internal consistency of the curated dataset.
"""

import pytest

from collatz.core import sequence, total_stopping_time
from collatz.library import (
    CATEGORY_LABELS,
    LIBRARY,
    LibraryEntry,
    all_entries,
    by_category,
    by_tag,
    categories,
    find_entry,
)


# ---------------------------------------------------------------------------
# LibraryEntry dataclass
# ---------------------------------------------------------------------------

class TestLibraryEntry:
    def test_str_contains_name_and_n(self) -> None:
        entry = LibraryEntry(
            n=27,
            name="Test",
            description="desc",
            category="test",
        )
        s = str(entry)
        assert "Test" in s
        assert "27" in s

    def test_optional_fields_default_none(self) -> None:
        entry = LibraryEntry(n=1, name="One", description="d", category="c")
        assert entry.stopping_time is None
        assert entry.peak_value is None
        assert entry.altitude is None
        assert entry.notes is None

    def test_frozen(self) -> None:
        entry = LibraryEntry(n=1, name="One", description="d", category="c")
        with pytest.raises((AttributeError, TypeError)):
            entry.n = 2  # type: ignore[misc]

    def test_tags_default_empty(self) -> None:
        entry = LibraryEntry(n=1, name="One", description="d", category="c")
        assert entry.tags == ()


# ---------------------------------------------------------------------------
# LIBRARY list integrity
# ---------------------------------------------------------------------------

class TestLibraryIntegrity:
    def test_library_nonempty(self) -> None:
        assert len(LIBRARY) > 0

    def test_all_n_positive(self) -> None:
        for e in LIBRARY:
            assert e.n >= 1, f"Entry {e.name!r} has n={e.n}"

    def test_all_names_nonempty(self) -> None:
        for e in LIBRARY:
            assert e.name.strip(), f"Entry n={e.n} has blank name"

    def test_all_descriptions_nonempty(self) -> None:
        for e in LIBRARY:
            assert e.description.strip(), f"Entry n={e.n} has blank description"

    def test_all_categories_in_category_labels(self) -> None:
        for e in LIBRARY:
            assert e.category in CATEGORY_LABELS, (
                f"Entry n={e.n} category {e.category!r} not in CATEGORY_LABELS"
            )

    def test_precomputed_stopping_times_correct(self) -> None:
        """Verify that any pre-computed stopping_time matches reality."""
        for e in LIBRARY:
            if e.stopping_time is not None:
                actual = total_stopping_time(e.n)
                assert actual == e.stopping_time, (
                    f"n={e.n} ({e.name}): library says {e.stopping_time} steps, "
                    f"computed {actual}"
                )

    def test_precomputed_peak_values_correct(self) -> None:
        """Verify that any pre-computed peak_value matches reality."""
        for e in LIBRARY:
            if e.peak_value is not None:
                actual_peak = max(sequence(e.n))
                assert actual_peak == e.peak_value, (
                    f"n={e.n} ({e.name}): library says peak={e.peak_value}, "
                    f"computed {actual_peak}"
                )

    def test_precomputed_altitudes_consistent(self) -> None:
        """Altitude must equal peak/n when both are provided."""
        for e in LIBRARY:
            if e.altitude is not None and e.peak_value is not None:
                expected = e.peak_value / e.n
                assert abs(e.altitude - expected) < 1.0, (
                    f"n={e.n} ({e.name}): altitude {e.altitude} not close to "
                    f"peak/n = {expected:.2f}"
                )

    def test_n27_present(self) -> None:
        ns = [e.n for e in LIBRARY]
        assert 27 in ns, "n=27 (The Celebrity) must be in the library"

    def test_n837799_present(self) -> None:
        ns = [e.n for e in LIBRARY]
        assert 837799 in ns, "n=837799 (Million Milestone) must be in the library"


# ---------------------------------------------------------------------------
# Accessor functions
# ---------------------------------------------------------------------------

class TestAllEntries:
    def test_returns_list(self) -> None:
        result = all_entries()
        assert isinstance(result, list)

    def test_same_length_as_library(self) -> None:
        assert len(all_entries()) == len(LIBRARY)

    def test_returns_copy(self) -> None:
        # Modifying the returned list must not affect LIBRARY.
        result = all_entries()
        result.clear()
        assert len(LIBRARY) > 0


class TestByCategory:
    def test_known_category_nonempty(self) -> None:
        assert len(by_category("long_trajectory")) > 0

    def test_unknown_category_empty(self) -> None:
        assert by_category("nonexistent_category") == []

    def test_all_results_have_correct_category(self) -> None:
        for cat in categories():
            for entry in by_category(cat):
                assert entry.category == cat

    def test_all_categories_have_entries(self) -> None:
        for cat in categories():
            assert len(by_category(cat)) > 0, f"Category {cat!r} has no entries"


class TestByTag:
    def test_famous_tag(self) -> None:
        results = by_tag("famous")
        assert len(results) > 0

    def test_all_results_carry_tag(self) -> None:
        for tag in ["famous", "record", "educational"]:
            for entry in by_tag(tag):
                assert tag in entry.tags

    def test_unknown_tag_empty(self) -> None:
        assert by_tag("no_such_tag_xyz") == []


class TestCategories:
    def test_returns_sorted_list(self) -> None:
        cats = categories()
        assert cats == sorted(cats)

    def test_long_trajectory_present(self) -> None:
        assert "long_trajectory" in categories()

    def test_structural_present(self) -> None:
        assert "structural" in categories()


class TestFindEntry:
    def test_n27_found(self) -> None:
        results = find_entry(27)
        assert len(results) > 0
        assert all(e.n == 27 for e in results)

    def test_unknown_n_returns_empty(self) -> None:
        # Use a large prime unlikely to be in the library.
        assert find_entry(999_999_937) == []

    def test_multiple_entries_for_same_n(self) -> None:
        # n=27 appears in multiple categories.
        results = find_entry(27)
        categories_found = {e.category for e in results}
        assert len(categories_found) >= 2, (
            "n=27 should appear in at least 2 categories"
        )


# ---------------------------------------------------------------------------
# CATEGORY_LABELS
# ---------------------------------------------------------------------------

class TestCategoryLabels:
    def test_all_categories_labelled(self) -> None:
        for cat in categories():
            assert cat in CATEGORY_LABELS, f"No label for category {cat!r}"

    def test_labels_nonempty(self) -> None:
        for cat, label in CATEGORY_LABELS.items():
            assert label.strip(), f"Label for {cat!r} is blank"
