"""
Tests for collatz.graph_export — build_collatz_graph, build_inverse_tree,
export_csv, export_image, and the private _force_layout helper.

All file-creating tests use pytest's tmp_path fixture so that generated
artefacts are isolated per test run and cleaned up automatically.
"""

from __future__ import annotations

import csv
import math
from pathlib import Path

import matplotlib
matplotlib.use("Agg")  # non-interactive backend; set before any pyplot import
import pytest

from collatz.core import step, sequence
from collatz.graph_export import (
    MAX_NODES,
    TYPE_CHOSEN,
    TYPE_EVEN_PRED,
    TYPE_ODD_PRED,
    TYPE_OTHER,
    TYPE_PATH,
    _force_layout,
    build_collatz_graph,
    build_inverse_tree,
    export_csv,
    export_image,
)


# ---------------------------------------------------------------------------
# build_collatz_graph()
# ---------------------------------------------------------------------------

class TestBuildCollatzGraph:
    def test_chosen_node_present(self) -> None:
        nodes, _ = build_collatz_graph(10)
        types = {v: t for v, t in nodes}
        assert types[10] == TYPE_CHOSEN

    def test_node_count_small_n(self) -> None:
        # For n <= MAX_NODES, all integers in [1, n] appear.
        nodes, _ = build_collatz_graph(15)
        values = [v for v, _ in nodes]
        assert sorted(values) == list(range(1, 16))

    def test_path_nodes_labelled(self) -> None:
        seq = sequence(10)
        nodes, _ = build_collatz_graph(10)
        types = {v: t for v, t in nodes}
        for val in seq:
            if val == 10:
                assert types[val] == TYPE_CHOSEN
            elif val in types:
                assert types[val] == TYPE_PATH

    def test_other_nodes_labelled(self) -> None:
        seq = sequence(10)
        path_set = set(seq)
        nodes, _ = build_collatz_graph(10)
        for v, t in nodes:
            if v not in path_set:
                assert t == TYPE_OTHER

    def test_edges_point_to_valid_successor(self) -> None:
        nodes, edges = build_collatz_graph(20)
        val_set = {v for v, _ in nodes}
        for src, dst in edges:
            assert step(src) == dst
            assert dst in val_set

    def test_node_one_has_no_outgoing_edge(self) -> None:
        _, edges = build_collatz_graph(10)
        sources = {src for src, _ in edges}
        assert 1 not in sources

    def test_large_n_falls_back_to_path_only(self) -> None:
        # For n > MAX_NODES the node set shrinks to the path.
        n = MAX_NODES + 1
        nodes, _ = build_collatz_graph(n)
        # Path-only: every node must appear in the sequence.
        path_set = set(sequence(n))
        for v, _ in nodes:
            assert v in path_set

    def test_precomputed_seq_accepted(self) -> None:
        seq = sequence(10)
        nodes1, edges1 = build_collatz_graph(10)
        nodes2, edges2 = build_collatz_graph(10, seq=seq)
        assert sorted(nodes1) == sorted(nodes2)
        assert sorted(edges1) == sorted(edges2)

    def test_n1_single_node(self) -> None:
        nodes, edges = build_collatz_graph(1)
        assert len(nodes) == 1
        assert nodes[0] == (1, TYPE_CHOSEN)
        assert edges == []

    def test_n2_two_nodes(self) -> None:
        nodes, edges = build_collatz_graph(2)
        values = {v for v, _ in nodes}
        assert values == {1, 2}
        # Edge from 2 to 1 (step(2)=1).
        assert (2, 1) in edges


# ---------------------------------------------------------------------------
# build_inverse_tree()
# ---------------------------------------------------------------------------

class TestBuildInverseTree:
    def test_root_is_chosen(self) -> None:
        nodes, _ = build_inverse_tree(4)
        types = dict(nodes)
        assert types[4] == TYPE_CHOSEN

    def test_depth_one_gives_direct_predecessors_only(self) -> None:
        nodes, edges = build_inverse_tree(4, depth=1)
        node_set = {v for v, _ in nodes}
        # Direct predecessors of 4: 8 (even) and 1 (odd, step(1)=4).
        assert 8 in node_set
        assert 1 in node_set
        # At depth 1, children of predecessors should NOT be present.
        # 2 is a predecessor of 1 but at depth 2.
        assert 2 not in node_set

    def test_even_pred_type(self) -> None:
        # 2*n is always an even predecessor.
        nodes, _ = build_inverse_tree(4, depth=1)
        types = dict(nodes)
        assert types[8] == TYPE_EVEN_PRED

    def test_odd_pred_type(self) -> None:
        # step(1) = 3*1+1 = 4, so 1 is the odd predecessor of 4.
        nodes, _ = build_inverse_tree(4, depth=1)
        types = dict(nodes)
        assert types[1] == TYPE_ODD_PRED

    def test_edges_parent_to_child(self) -> None:
        # Every edge (parent, child) must satisfy step(child) == parent.
        nodes, edges = build_inverse_tree(10, depth=4)
        for parent, child in edges:
            assert step(child) == parent, (
                f"step({child}) should be {parent}, got {step(child)}"
            )

    def test_no_duplicate_nodes(self) -> None:
        nodes, _ = build_inverse_tree(27, depth=5)
        values = [v for v, _ in nodes]
        assert len(values) == len(set(values))

    def test_depth_zero_gives_only_root(self) -> None:
        nodes, edges = build_inverse_tree(7, depth=0)
        assert len(nodes) == 1
        assert nodes[0][0] == 7
        assert edges == []

    def test_precomputed_seq_accepted(self) -> None:
        seq = sequence(4)
        nodes1, edges1 = build_inverse_tree(4, depth=3)
        nodes2, edges2 = build_inverse_tree(4, depth=3, seq=seq)
        assert sorted(nodes1) == sorted(nodes2)
        assert sorted(edges1) == sorted(edges2)

    def test_n1_root(self) -> None:
        nodes, edges = build_inverse_tree(1, depth=2)
        types = dict(nodes)
        assert types[1] == TYPE_CHOSEN
        # 2 is an even predecessor of 1.
        assert 2 in types


# ---------------------------------------------------------------------------
# export_csv()
# ---------------------------------------------------------------------------

class TestExportCsv:
    def _build_small(self):
        return build_collatz_graph(10)

    def test_creates_two_files(self, tmp_path: Path) -> None:
        nodes, edges = self._build_small()
        out = tmp_path / "graph.csv"
        n_path, e_path = export_csv(nodes, edges, str(out))
        assert Path(n_path).exists()
        assert Path(e_path).exists()

    def test_nodes_file_has_header(self, tmp_path: Path) -> None:
        nodes, edges = self._build_small()
        n_path, _ = export_csv(nodes, edges, str(tmp_path / "g.csv"))
        with open(n_path, newline="") as f:
            reader = csv.reader(f)
            header = next(reader)
        assert header == ["id", "type"]

    def test_edges_file_has_header(self, tmp_path: Path) -> None:
        nodes, edges = self._build_small()
        _, e_path = export_csv(nodes, edges, str(tmp_path / "g.csv"))
        with open(e_path, newline="") as f:
            reader = csv.reader(f)
            header = next(reader)
        assert header == ["source", "target"]

    def test_nodes_file_row_count(self, tmp_path: Path) -> None:
        nodes, edges = self._build_small()
        n_path, _ = export_csv(nodes, edges, str(tmp_path / "g.csv"))
        with open(n_path, newline="") as f:
            rows = list(csv.reader(f))
        # header + one row per node
        assert len(rows) == len(nodes) + 1

    def test_edges_file_row_count(self, tmp_path: Path) -> None:
        nodes, edges = self._build_small()
        _, e_path = export_csv(nodes, edges, str(tmp_path / "g.csv"))
        with open(e_path, newline="") as f:
            rows = list(csv.reader(f))
        assert len(rows) == len(edges) + 1

    def test_suffix_insertion(self, tmp_path: Path) -> None:
        nodes, edges = self._build_small()
        n_path, e_path = export_csv(nodes, edges, str(tmp_path / "out.csv"))
        assert n_path.endswith("_nodes.csv")
        assert e_path.endswith("_edges.csv")

    def test_empty_graph(self, tmp_path: Path) -> None:
        n_path, e_path = export_csv([], [], str(tmp_path / "empty.csv"))
        with open(n_path, newline="") as f:
            rows = list(csv.reader(f))
        assert rows == [["id", "type"]]


# ---------------------------------------------------------------------------
# export_image()
# ---------------------------------------------------------------------------

class TestExportImage:
    def test_creates_png(self, tmp_path: Path) -> None:
        nodes, edges = build_collatz_graph(10)
        out = str(tmp_path / "g.png")
        export_image(nodes, edges, out)
        assert Path(out).exists()
        assert Path(out).stat().st_size > 0

    def test_creates_svg(self, tmp_path: Path) -> None:
        nodes, edges = build_collatz_graph(10)
        out = str(tmp_path / "g.svg")
        export_image(nodes, edges, out)
        assert Path(out).exists()

    def test_unsupported_extension_raises(self, tmp_path: Path) -> None:
        nodes, edges = build_collatz_graph(5)
        with pytest.raises(ValueError, match="Unsupported"):
            export_image(nodes, edges, str(tmp_path / "g.txt"))

    def test_empty_graph_no_crash(self, tmp_path: Path) -> None:
        out = str(tmp_path / "empty.png")
        export_image([], [], out)
        assert Path(out).exists()

    def test_inverse_tree_png(self, tmp_path: Path) -> None:
        nodes, edges = build_inverse_tree(4, depth=3)
        out = str(tmp_path / "inv.png")
        export_image(nodes, edges, out, title="Inverse tree test")
        assert Path(out).exists()
        assert Path(out).stat().st_size > 0


# ---------------------------------------------------------------------------
# _force_layout()
# ---------------------------------------------------------------------------

class TestForceLayout:
    def test_empty_returns_empty(self) -> None:
        assert _force_layout([], []) == {}

    def test_single_node_at_origin(self) -> None:
        result = _force_layout([42], [])
        assert result == {42: (0.0, 0.0)}

    def test_returns_all_nodes(self) -> None:
        ids = list(range(1, 11))
        edges = [(i, i + 1) for i in range(1, 10)]
        result = _force_layout(ids, edges, n_iter=10)
        assert set(result.keys()) == set(ids)

    def test_positions_are_finite(self) -> None:
        ids = list(range(1, 20))
        edges = [(i, i + 1) for i in range(1, 19)]
        result = _force_layout(ids, edges, n_iter=50)
        for nid, (x, y) in result.items():
            assert math.isfinite(x), f"x for node {nid} is not finite"
            assert math.isfinite(y), f"y for node {nid} is not finite"

    def test_two_nodes_separate(self) -> None:
        # Repulsion should push nodes apart from the same starting position.
        result = _force_layout([1, 2], [(1, 2)], n_iter=100)
        x1, y1 = result[1]
        x2, y2 = result[2]
        dist = math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)
        assert dist > 0.01  # nodes must not collapse to the same point

    def test_disconnected_graph(self) -> None:
        # A graph with no edges should still layout without error.
        ids = list(range(1, 6))
        result = _force_layout(ids, [], n_iter=30)
        assert len(result) == 5
