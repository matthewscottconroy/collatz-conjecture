"""
Collatz graph export for the CLI and scripting.

Two graph types are supported:

``collatz``
    The *forward* Collatz graph.  Nodes are the positive integers in ``[1, n]``
    (or, for large ``n``, only the values that appear on ``n``'s path to 1).
    Each node has a directed edge to its Collatz successor when the successor
    is also in the node set.

``inverse``
    The *inverse predecessor tree* rooted at ``n``.  Every node ``m`` in the
    tree satisfies ``step(m) = parent``, so ``m``'s Collatz sequence passes
    through ``n`` on its way to 1.  The tree is expanded by BFS up to a
    caller-specified depth.

Output formats
--------------
CSV
    Two files are written: ``{base}_nodes.csv`` (columns: ``id``, ``type``)
    and ``{base}_edges.csv`` (columns: ``source``, ``target``).  These files
    are importable into Gephi, Cytoscape, D3.js, and other network tools.

PNG / SVG
    A self-contained image rendered with matplotlib using a synchronous
    spring–repulsion force-directed layout.  Suitable for publication-quality
    output with ``--output graph.svg`` or quick inspection with ``--output
    graph.png``.

Node type labels
----------------
``chosen``
    The starting value ``n`` itself.
``path``
    A value (other than ``n``) that appears in ``n``'s forward sequence to 1.
``other``
    Every other integer in ``[1, n]``.
``even_predecessor``
    An inverse-tree node reached via the even branch (predecessor ``= 2k``).
``odd_predecessor``
    An inverse-tree node reached via the odd branch
    (predecessor ``= (k-1) // 3`` when valid).

Example
-------
::

    from collatz.graph_export import build_collatz_graph, export_image, export_csv

    # Forward graph for n=27, save as PNG
    nodes, edges = build_collatz_graph(27)
    export_image(nodes, edges, "collatz_27.png", title="Collatz graph n=27")

    # Inverse tree, save as CSV
    nodes, edges = build_inverse_tree(27, depth=5)
    n_file, e_file = export_csv(nodes, edges, "inverse_27.csv")
"""

from __future__ import annotations

import csv
import math
from collections import deque
from pathlib import Path

# Maximum nodes rendered in full {1..n} mode before falling back to path-only.
MAX_NODES = 300

# ── Node type constants ────────────────────────────────────────────────────
TYPE_CHOSEN    = "chosen"
TYPE_PATH      = "path"
TYPE_OTHER     = "other"
TYPE_EVEN_PRED = "even_predecessor"
TYPE_ODD_PRED  = "odd_predecessor"

# ── Colour map (Catppuccin Mocha) used by export_image ────────────────────
_NODE_COLOURS: dict[str, str] = {
    TYPE_CHOSEN:    "#89b4fa",   # blue
    TYPE_PATH:      "#f9e2af",   # yellow
    TYPE_OTHER:     "#45475a",   # dim grey
    TYPE_EVEN_PRED: "#94e2d5",   # teal
    TYPE_ODD_PRED:  "#fab387",   # peach
}
_NODE_LABELS: dict[str, str] = {
    TYPE_CHOSEN:    "Chosen n",
    TYPE_PATH:      "On path to 1",
    TYPE_OTHER:     "Other",
    TYPE_EVEN_PRED: "Even predecessor (2k)",
    TYPE_ODD_PRED:  "Odd predecessor ((k−1)/3)",
}


# ---------------------------------------------------------------------------
# Graph builders
# ---------------------------------------------------------------------------

def build_collatz_graph(
    n: int,
    seq: list[int] | None = None,
) -> tuple[list[tuple[int, str]], list[tuple[int, int]]]:
    """Build the forward Collatz directed graph for starting value *n*.

    Nodes are all positive integers in ``[1, n]``.  When ``n > MAX_NODES``
    (300) only the values that appear on ``n``'s own path to 1 are included,
    keeping the output usable at any scale.

    Each node carries an edge to ``step(v)`` whenever the successor is also a
    node in the graph.

    Args:
        n:   Starting positive integer.
        seq: Pre-computed sequence ``[n, …, 1]``.  Computed internally when
             omitted — pass a cached copy to avoid redundant work.

    Returns:
        A 2-tuple ``(nodes, edges)`` where

        * ``nodes`` is a list of ``(value, type_label)`` pairs, with
          ``type_label`` in ``{chosen, path, other}``.
        * ``edges`` is a list of ``(source, target)`` integer pairs.

    Raises:
        CollatzError: If ``n`` is not a positive integer.

    Example::

        nodes, edges = build_collatz_graph(10)
        # nodes: [(1,'path'), (2,'path'), ..., (10,'chosen')]
        # edges: [(2,1), (4,2), (6,3), (8,4), (10,5), (3,10), ...]
    """
    from collatz.core import sequence as _seq, step as _step

    if seq is None:
        seq = _seq(n)
    path_set = set(seq)

    if n <= MAX_NODES:
        values: list[int] = list(range(1, n + 1))
    else:
        values = sorted(path_set)

    val_set = set(values)

    nodes: list[tuple[int, str]] = []
    for v in values:
        if v == n:
            label = TYPE_CHOSEN
        elif v in path_set:
            label = TYPE_PATH
        else:
            label = TYPE_OTHER
        nodes.append((v, label))

    edges: list[tuple[int, int]] = []
    for v, _ in nodes:
        if v == 1:
            continue
        succ = _step(v)
        if succ in val_set:
            edges.append((v, succ))

    return nodes, edges


def build_inverse_tree(
    n: int,
    depth: int = 6,
    seq: list[int] | None = None,
) -> tuple[list[tuple[int, str]], list[tuple[int, int]]]:
    """Build the inverse predecessor tree rooted at *n*.

    Starting from ``n``, expand predecessors by BFS up to ``depth`` levels.
    Each step in the BFS computes ``get_predecessors(current)`` and records
    whether each predecessor arrived via the even branch (``2k``) or the odd
    branch (``(k-1)//3``).

    Nodes that also appear on ``n``'s forward path to 1 are marked
    ``"chosen"`` (for ``n`` itself) or with their predecessor type otherwise
    (the forward path rarely intersects the inverse tree except at the trivial
    cycle 4→2→1→4).

    Args:
        n:     Starting positive integer (root of the tree).
        depth: Maximum expansion depth.  Depth 1 shows only the direct
               predecessors of ``n``; depth 6 (default) gives a moderately
               sized tree suitable for visualisation.
        seq:   Pre-computed forward sequence (used only for the ``chosen``
               node label on the root).

    Returns:
        A 2-tuple ``(nodes, edges)`` where

        * ``nodes`` is a list of ``(value, type_label)`` pairs, with
          ``type_label`` in ``{chosen, even_predecessor, odd_predecessor}``.
        * ``edges`` is a list of ``(parent, child)`` integer pairs directed
          away from the root toward the leaves.

    Raises:
        CollatzError: If ``n`` is not a positive integer.

    Example::

        nodes, edges = build_inverse_tree(4, depth=2)
        # Includes: 4 (chosen), 8 (even), 1 (odd, since step(1)=4),
        #           16 (even of 8), 2 (even of 1)
    """
    from collatz.core import get_predecessors

    node_type: dict[int, str] = {n: TYPE_CHOSEN}
    edges_out: list[tuple[int, int]] = []
    visited: set[int] = {n}
    queue: deque[tuple[int, int]] = deque([(n, 0)])

    while queue:
        curr, d = queue.popleft()
        if d >= depth:
            continue
        preds = get_predecessors(curr)
        even_pred = preds[0]   # 2*curr is always first
        for pred in preds:
            if pred in visited:
                continue
            visited.add(pred)
            node_type[pred] = (
                TYPE_EVEN_PRED if pred == even_pred else TYPE_ODD_PRED
            )
            edges_out.append((curr, pred))
            queue.append((pred, d + 1))

    nodes: list[tuple[int, str]] = list(node_type.items())
    return nodes, edges_out


# ---------------------------------------------------------------------------
# Exporters
# ---------------------------------------------------------------------------

def export_csv(
    nodes: list[tuple[int, str]],
    edges: list[tuple[int, int]],
    output_path: str,
) -> tuple[str, str]:
    """Write graph data to two CSV files.

    The node file has columns ``id, type``; the edge file has columns
    ``source, target``.  Both files are ready to import into Gephi,
    Cytoscape, or any tool that accepts separate node/edge tables.

    Args:
        nodes:       List of ``(value, type_label)`` pairs.
        edges:       List of ``(source, target)`` integer pairs.
        output_path: Base output path.  Suffixes ``_nodes`` and ``_edges``
                     are inserted before the extension, so
                     ``"graph.csv"`` becomes ``"graph_nodes.csv"`` and
                     ``"graph_edges.csv"``.

    Returns:
        A ``(nodes_path, edges_path)`` tuple of the actual file paths written.

    Example::

        n_file, e_file = export_csv(nodes, edges, "out/graph.csv")
        print(f"Nodes → {n_file}")
        print(f"Edges → {e_file}")
    """
    base = Path(output_path).with_suffix("")
    ext  = Path(output_path).suffix or ".csv"

    nodes_path = f"{base}_nodes{ext}"
    edges_path = f"{base}_edges{ext}"

    with open(nodes_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["id", "type"])
        w.writerows(nodes)

    with open(edges_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["source", "target"])
        w.writerows(edges)

    return nodes_path, edges_path


def export_image(
    nodes: list[tuple[int, str]],
    edges: list[tuple[int, int]],
    output_path: str,
    *,
    title: str = "",
    n_iter: int = 300,
    figsize: tuple[float, float] = (12.0, 12.0),
) -> None:
    """Render the graph to a PNG or SVG using matplotlib.

    Node positions are computed by a synchronous spring–repulsion
    force-directed algorithm run to near-convergence.  The image uses the
    same Catppuccin Mocha dark-mode palette as the GUI.

    Args:
        nodes:       List of ``(value, type_label)`` pairs.
        edges:       List of ``(source, target)`` integer pairs.
        output_path: Destination file.  The extension determines the format:
                     ``.png`` or ``.svg`` (any resolution for SVG).
        title:       Optional title string drawn at the top of the figure.
        n_iter:      Number of force-directed layout iterations.  More
                     iterations produce a more settled layout at the cost of
                     slightly longer render time (default 300).
        figsize:     Matplotlib figure size in inches ``(width, height)``.

    Raises:
        ValueError: If ``output_path`` has an unsupported extension.

    Example::

        nodes, edges = build_collatz_graph(27)
        export_image(nodes, edges, "collatz_27.png",
                     title="Collatz graph  n=27")
    """
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches

    ext = Path(output_path).suffix.lower()
    if ext not in {".png", ".svg", ".pdf"}:
        raise ValueError(
            f"Unsupported image format {ext!r}.  Use .png, .svg, or .pdf."
        )

    node_ids = [v for v, _ in nodes]
    positions = _force_layout(node_ids, edges, n_iter=n_iter)

    fig, ax = plt.subplots(figsize=figsize)
    fig.patch.set_facecolor("#1e1e2e")
    ax.set_facecolor("#1e1e2e")
    ax.axis("off")

    # Edges
    for src, dst in edges:
        if src not in positions or dst not in positions:
            continue
        x1, y1 = positions[src]
        x2, y2 = positions[dst]
        ax.annotate(
            "",
            xy=(x2, y2), xytext=(x1, y1),
            arrowprops=dict(
                arrowstyle="-|>", color="#585b70",
                lw=0.7, mutation_scale=10,
            ),
        )

    # Nodes
    for v, ntype in nodes:
        x, y = positions[v]
        colour = _NODE_COLOURS.get(ntype, "#45475a")
        text_col = "#1e1e2e" if colour != "#45475a" else "#cdd6f4"
        n_nodes = len(nodes)
        node_size = max(80, min(600, 3000 // max(n_nodes, 1)))
        font_size = max(4, min(8, 160 // max(n_nodes, 1)))
        ax.scatter([x], [y], s=node_size, c=colour, zorder=5, linewidths=0)
        ax.text(x, y, str(v), ha="center", va="center",
                fontsize=font_size, fontweight="bold",
                color=text_col, zorder=6)

    if title:
        ax.set_title(title, color="#cdd6f4", fontsize=11, pad=12)

    # Legend
    seen_types = {t for _, t in nodes}
    handles = [
        mpatches.Patch(
            color=_NODE_COLOURS[t],
            label=_NODE_LABELS[t],
        )
        for t in [
            TYPE_CHOSEN, TYPE_PATH, TYPE_OTHER,
            TYPE_EVEN_PRED, TYPE_ODD_PRED,
        ]
        if t in seen_types
    ]
    if handles:
        ax.legend(
            handles=handles, loc="upper right",
            framealpha=0.35, facecolor="#2a2a3e",
            edgecolor="#45475a", labelcolor="#cdd6f4", fontsize=8,
        )

    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches="tight",
                facecolor=fig.get_facecolor())
    plt.close(fig)


# ---------------------------------------------------------------------------
# Force-directed layout
# ---------------------------------------------------------------------------

def _force_layout(
    node_ids: list[int],
    edges: list[tuple[int, int]],
    *,
    n_iter: int = 300,
) -> dict[int, tuple[float, float]]:
    """Run a spring–repulsion force-directed layout to near-convergence.

    Uses a circular initial arrangement, pairwise Coulomb repulsion, and
    Hooke springs along edges.  Velocity is damped each iteration so the
    system settles rather than oscillating.

    Args:
        node_ids: List of node identifiers (integers).
        edges:    List of ``(source, target)`` pairs.
        n_iter:   Number of integration steps (default 300).

    Returns:
        Mapping ``{node_id: (x, y)}`` of final positions.
    """
    n = len(node_ids)
    if n == 0:
        return {}
    if n == 1:
        return {node_ids[0]: (0.0, 0.0)}

    # Circular initial positions scaled to graph size
    scale = max(1.0, n * 0.12)
    pos: dict[int, list[float]] = {}
    for i, nid in enumerate(node_ids):
        angle = 2.0 * math.pi * i / n
        pos[nid] = [math.cos(angle) * scale, math.sin(angle) * scale]

    idx = {nid: i for i, nid in enumerate(node_ids)}
    vel: list[list[float]] = [[0.0, 0.0] for _ in node_ids]

    repulsion = max(0.5, scale ** 2 * 0.15)
    spring_k  = 0.04
    rest_len  = max(1.0, scale * 0.6)
    damping   = 0.88

    for _ in range(n_iter):
        forces: list[list[float]] = [[0.0, 0.0] for _ in node_ids]

        # Pairwise repulsion (O(n²))
        for i in range(n):
            ni = node_ids[i]
            for j in range(i + 1, n):
                nj = node_ids[j]
                dx = pos[ni][0] - pos[nj][0]
                dy = pos[ni][1] - pos[nj][1]
                d2 = dx * dx + dy * dy + 0.01
                d  = math.sqrt(d2)
                f  = repulsion / d2
                fx, fy = f * dx / d, f * dy / d
                forces[i][0] += fx;  forces[i][1] += fy
                forces[j][0] -= fx;  forces[j][1] -= fy

        # Spring attraction along edges
        for src, dst in edges:
            if src not in idx or dst not in idx:
                continue
            si, di = idx[src], idx[dst]
            dx = pos[dst][0] - pos[src][0]
            dy = pos[dst][1] - pos[src][1]
            d  = math.sqrt(dx * dx + dy * dy) + 0.001
            f  = spring_k * (d - rest_len)
            fx, fy = f * dx / d, f * dy / d
            forces[si][0] += fx;  forces[si][1] += fy
            forces[di][0] -= fx;  forces[di][1] -= fy

        # Integrate with damping
        for i in range(n):
            vel[i][0] = (vel[i][0] + forces[i][0]) * damping
            vel[i][1] = (vel[i][1] + forces[i][1]) * damping
            pos[node_ids[i]][0] += vel[i][0]
            pos[node_ids[i]][1] += vel[i][1]

    return {nid: (pos[nid][0], pos[nid][1]) for nid in node_ids}
