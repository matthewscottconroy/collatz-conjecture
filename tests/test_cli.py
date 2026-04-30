"""
Tests for the CLI entry points defined in main.py.

Strategy
--------
- _cli_explore and _cli_scan are tested by capturing stdout with capsys and
  asserting the printed output contains expected values.
- _cli_graph is tested by checking that files are created on disk with
  non-trivial content, using pytest's tmp_path fixture for isolation.
- argparse integration is tested via main() with monkeypatched sys.argv.

All matplotlib rendering is forced into the Agg (non-interactive) backend
before any import that might trigger it.
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import pytest

# Import the functions under test.  They live at module level in main.py.
import main as cli_module
from main import _cli_explore, _cli_graph, _cli_scan


# ---------------------------------------------------------------------------
# _cli_explore()
# ---------------------------------------------------------------------------

class TestCliExplore:
    def test_output_contains_n(self, capsys) -> None:
        _cli_explore(27)
        captured = capsys.readouterr()
        assert "27" in captured.out

    def test_stopping_time_n27(self, capsys) -> None:
        _cli_explore(27)
        captured = capsys.readouterr()
        assert "111" in captured.out

    def test_peak_value_n27(self, capsys) -> None:
        _cli_explore(27)
        captured = capsys.readouterr()
        # Peak of 27 is 9232, printed as "9,232" by the summary formatter.
        assert "9,232" in captured.out

    def test_summary_labels_present(self, capsys) -> None:
        _cli_explore(27)
        captured = capsys.readouterr()
        assert "Stopping time" in captured.out
        assert "Peak value" in captured.out
        assert "Altitude" in captured.out

    def test_n1_no_crash(self, capsys) -> None:
        _cli_explore(1)
        captured = capsys.readouterr()
        assert "1" in captured.out

    def test_large_n(self, capsys) -> None:
        _cli_explore(837799)
        captured = capsys.readouterr()
        # Large n is printed as "837,799" by the summary formatter.
        assert "837,799" in captured.out


# ---------------------------------------------------------------------------
# _cli_scan()
# ---------------------------------------------------------------------------

class TestCliScan:
    def test_default_metric_header(self, capsys) -> None:
        _cli_scan(1, 50)
        captured = capsys.readouterr()
        assert "stopping_time" in captured.out

    def test_correct_number_of_result_rows(self, capsys) -> None:
        _cli_scan(1, 100)
        captured = capsys.readouterr()
        # Output has a header line, a separator, and up to 10 result rows.
        lines = [l for l in captured.out.splitlines() if l.strip()]
        # At least the 10 result rows plus header lines.
        assert len(lines) >= 10

    def test_sorted_descending(self, capsys) -> None:
        _cli_scan(1, 100, metric="stopping_time")
        captured = capsys.readouterr()
        # Extract lines that contain numeric data (skip header/separator).
        data_lines = [
            l for l in captured.out.splitlines()
            if l.strip() and not l.startswith("Top") and "---" not in l
            and "score" not in l
        ]
        scores = []
        for line in data_lines:
            parts = line.split()
            if len(parts) >= 2:
                try:
                    scores.append(float(parts[-1]))
                except ValueError:
                    pass
        if len(scores) >= 2:
            assert scores == sorted(scores, reverse=True)

    def test_altitude_metric(self, capsys) -> None:
        _cli_scan(1, 50, metric="altitude")
        captured = capsys.readouterr()
        assert "altitude" in captured.out

    def test_small_range(self, capsys) -> None:
        _cli_scan(5, 7)
        captured = capsys.readouterr()
        # Only 3 values in range; output must mention the range.
        assert "5" in captured.out
        assert "7" in captured.out

    def test_single_value_range(self, capsys) -> None:
        _cli_scan(27, 27)
        captured = capsys.readouterr()
        assert "27" in captured.out


# ---------------------------------------------------------------------------
# _cli_graph() — forward graph
# ---------------------------------------------------------------------------

class TestCliGraphCollatz:
    def test_creates_png(self, tmp_path: Path) -> None:
        out = str(tmp_path / "graph.png")
        _cli_graph(10, out, graph_type="collatz")
        assert Path(out).exists()
        assert Path(out).stat().st_size > 0

    def test_creates_svg(self, tmp_path: Path) -> None:
        out = str(tmp_path / "graph.svg")
        _cli_graph(10, out, graph_type="collatz")
        assert Path(out).exists()

    def test_creates_csv_pair(self, tmp_path: Path) -> None:
        out = str(tmp_path / "graph.csv")
        _cli_graph(10, out, graph_type="collatz")
        assert Path(tmp_path / "graph_nodes.csv").exists()
        assert Path(tmp_path / "graph_edges.csv").exists()

    def test_csv_nodes_have_correct_header(self, tmp_path: Path) -> None:
        out = str(tmp_path / "graph.csv")
        _cli_graph(10, out, graph_type="collatz")
        with open(tmp_path / "graph_nodes.csv", newline="") as f:
            header = next(csv.reader(f))
        assert header == ["id", "type"]

    def test_csv_edges_have_correct_header(self, tmp_path: Path) -> None:
        out = str(tmp_path / "graph.csv")
        _cli_graph(10, out, graph_type="collatz")
        with open(tmp_path / "graph_edges.csv", newline="") as f:
            header = next(csv.reader(f))
        assert header == ["source", "target"]

    def test_stdout_reports_node_count(self, tmp_path: Path, capsys) -> None:
        out = str(tmp_path / "g.png")
        _cli_graph(10, out, graph_type="collatz")
        captured = capsys.readouterr()
        assert "nodes" in captured.out

    def test_unsupported_format_exits(self, tmp_path: Path) -> None:
        out = str(tmp_path / "graph.xyz")
        with pytest.raises(SystemExit):
            _cli_graph(10, out, graph_type="collatz")


# ---------------------------------------------------------------------------
# _cli_graph() — inverse tree
# ---------------------------------------------------------------------------

class TestCliGraphInverse:
    def test_creates_png(self, tmp_path: Path) -> None:
        out = str(tmp_path / "inv.png")
        _cli_graph(4, out, graph_type="inverse", depth=3)
        assert Path(out).exists()
        assert Path(out).stat().st_size > 0

    def test_creates_csv_pair(self, tmp_path: Path) -> None:
        out = str(tmp_path / "inv.csv")
        _cli_graph(4, out, graph_type="inverse", depth=2)
        assert Path(tmp_path / "inv_nodes.csv").exists()
        assert Path(tmp_path / "inv_edges.csv").exists()

    def test_depth_1_gives_small_tree(self, tmp_path: Path) -> None:
        out = str(tmp_path / "inv.csv")
        _cli_graph(4, out, graph_type="inverse", depth=1)
        with open(tmp_path / "inv_nodes.csv", newline="") as f:
            rows = list(csv.reader(f))
        # depth=1: root + direct predecessors of 4 (at most 3 nodes total).
        node_count = len(rows) - 1  # exclude header
        assert node_count <= 3


# ---------------------------------------------------------------------------
# argparse integration — main() dispatcher
# ---------------------------------------------------------------------------

class TestMainDispatch:
    def test_cli_flag_dispatches(self, monkeypatch, capsys) -> None:
        monkeypatch.setattr(sys, "argv", ["collatz-explorer", "--cli", "27"])
        with pytest.raises(SystemExit) as exc_info:
            cli_module.main()
        assert exc_info.value.code == 0
        assert "27" in capsys.readouterr().out

    def test_scan_flag_dispatches(self, monkeypatch, capsys) -> None:
        monkeypatch.setattr(sys, "argv", ["collatz-explorer", "--scan", "1", "20"])
        with pytest.raises(SystemExit) as exc_info:
            cli_module.main()
        assert exc_info.value.code == 0
        captured = capsys.readouterr()
        assert "stopping_time" in captured.out

    def test_graph_flag_dispatches(self, monkeypatch, capsys, tmp_path) -> None:
        out = str(tmp_path / "g.png")
        monkeypatch.setattr(
            sys, "argv",
            ["collatz-explorer", "--graph", "10", "--output", out],
        )
        with pytest.raises(SystemExit) as exc_info:
            cli_module.main()
        assert exc_info.value.code == 0
        assert Path(out).exists()

    def test_inverse_flag_dispatches(self, monkeypatch, capsys, tmp_path) -> None:
        out = str(tmp_path / "inv.png")
        monkeypatch.setattr(
            sys, "argv",
            ["collatz-explorer", "--inverse", "4", "--depth", "2", "--output", out],
        )
        with pytest.raises(SystemExit) as exc_info:
            cli_module.main()
        assert exc_info.value.code == 0
        assert Path(out).exists()

    def test_full_flag_dispatches(self, monkeypatch, capsys, tmp_path) -> None:
        out = str(tmp_path / "stats.csv")
        monkeypatch.setattr(
            sys, "argv",
            ["collatz-explorer", "--scan", "1", "10", "--full", "--output", out],
        )
        with pytest.raises(SystemExit) as exc_info:
            cli_module.main()
        assert exc_info.value.code == 0
        assert Path(out).exists()


# ---------------------------------------------------------------------------
# _cli_scan() --full
# ---------------------------------------------------------------------------

class TestCliScanFull:
    def test_creates_csv(self, tmp_path: Path) -> None:
        out = str(tmp_path / "stats.csv")
        _cli_scan(1, 10, full=True, output=out)
        assert Path(out).exists()

    def test_csv_has_correct_header(self, tmp_path: Path) -> None:
        out = str(tmp_path / "stats.csv")
        _cli_scan(1, 5, full=True, output=out)
        with open(out, newline="") as f:
            header = next(csv.reader(f))
        assert header == [
            "n", "stopping_time", "peak_value", "altitude", "glide",
            "oscillation_index", "band_persistence", "near_cycle_score",
            "even_steps", "odd_steps", "odd_fraction",
        ]

    def test_csv_row_count_matches_range(self, tmp_path: Path) -> None:
        out = str(tmp_path / "stats.csv")
        _cli_scan(1, 20, full=True, output=out)
        with open(out, newline="") as f:
            rows = list(csv.reader(f))
        # One header row + 20 data rows.
        assert len(rows) == 21

    def test_csv_n_column_matches_range(self, tmp_path: Path) -> None:
        out = str(tmp_path / "stats.csv")
        _cli_scan(5, 9, full=True, output=out)
        with open(out, newline="") as f:
            reader = csv.DictReader(f)
            ns = [int(row["n"]) for row in reader]
        assert ns == [5, 6, 7, 8, 9]

    def test_default_output_filename(self, capsys, monkeypatch, tmp_path: Path) -> None:
        monkeypatch.chdir(tmp_path)
        _cli_scan(1, 3, full=True)
        assert (tmp_path / "collatz_stats_1_3.csv").exists()

    def test_stdout_reports_written_rows(self, tmp_path: Path, capsys) -> None:
        out = str(tmp_path / "stats.csv")
        _cli_scan(1, 5, full=True, output=out)
        captured = capsys.readouterr()
        assert "5" in captured.out
        assert "rows" in captured.out
