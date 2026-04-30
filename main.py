#!/usr/bin/env python3
"""
Collatz Conjecture Explorer — entry point.

GUI mode (default)
------------------
Launch the interactive tkinter application::

    python main.py

The GUI has eight tabs:

  Trajectory      Step-by-step value plot (linear and log scale)
  Phase Plot      seq[k] vs seq[k+1] phase portrait
  Parity & Rhythm Even/odd parity raster, bit-length walk, odd-step gap histogram
  Range Scan      Bar chart, scatter, heatmap, record holders, trajectory fingerprint
  Compare         Overlay multiple sequences on one canvas
  Graph           Interactive force-directed Collatz graph with drag support
  Inverse Tree    Inverse predecessor tree with adjustable depth

CLI — trajectory statistics
----------------------------
Print all metrics for a single starting value (no GUI required)::

    python main.py --cli 27
    python main.py --cli 837799

CLI — range scan
-----------------
Print the top-10 starting values in a range ranked by a metric::

    python main.py --scan 1 1000
    python main.py --scan 1 1000 --metric altitude
    python main.py --scan 1 1000 --metric oscillation_index

Available ``--metric`` values:
  stopping_time, altitude, oscillation_index, band_persistence, near_cycle_score

CLI — graph export
------------------
Export the *forward* Collatz directed graph for n as PNG, SVG, or CSV::

    python main.py --graph 27 --output collatz_27.png
    python main.py --graph 27 --output collatz_27.svg
    python main.py --graph 27 --output collatz_27.csv

The CSV option writes two files: ``collatz_27_nodes.csv`` and
``collatz_27_edges.csv``, suitable for import into Gephi or Cytoscape.

Export the *inverse predecessor tree* rooted at n::

    python main.py --inverse 27 --output tree_27.png
    python main.py --inverse 27 --depth 8 --output tree_27_deep.svg
    python main.py --inverse 27 --depth 4 --output tree_27.csv

When ``--output`` is omitted a default filename is generated automatically.
"""

from __future__ import annotations

import argparse
import sys


# ---------------------------------------------------------------------------
# CLI helpers
# ---------------------------------------------------------------------------

def _cli_explore(n: int) -> None:
    """Print all trajectory statistics for the Collatz sequence from *n*.

    Args:
        n: Starting positive integer.
    """
    from collatz.analysis import compute_stats
    stats = compute_stats(n)
    print(stats.summary())


def _cli_scan(
    start: int,
    end: int,
    metric: str = "stopping_time",
    full: bool = False,
    output: str | None = None,
) -> None:
    """Print (or export) Collatz statistics for every value in [start, end].

    Args:
        start:  Inclusive lower bound (≥ 1).
        end:    Inclusive upper bound.
        metric: Ranking metric (ignored when *full* is True).
        full:   When True, write all metrics for every n to a CSV instead of
                printing the top-10.
        output: Destination path for CSV output (only used when *full* is True).
    """
    total = end - start + 1
    show_progress = total > 500

    def _progress(done: int, tot: int) -> None:
        if not show_progress:
            return
        pct = done / tot * 100
        filled = int(30 * done / tot)
        bar = "=" * filled + " " * (30 - filled)
        print(f"\r  [{bar}] {done:,}/{tot:,} ({pct:.0f}%)",
              end="", flush=True)

    if full:
        import csv as _csv
        from collatz.analysis import compute_stats
        out_path = output or f"collatz_stats_{start}_{end}.csv"
        if show_progress:
            print(f"Scanning [{start:,}, {end:,}] — writing all metrics to {out_path}")
        with open(out_path, "w", newline="") as f:
            writer = _csv.writer(f)
            writer.writerow([
                "n", "stopping_time", "peak_value", "altitude", "glide",
                "oscillation_index", "band_persistence", "near_cycle_score",
                "even_steps", "odd_steps", "odd_fraction",
            ])
            for i, n in enumerate(range(start, end + 1), 1):
                _progress(i, total)
                s = compute_stats(n)
                writer.writerow([
                    s.n, s.stopping_time, s.peak_value,
                    f"{s.altitude:.6f}", s.glide,
                    f"{s.oscillation_index:.6f}", f"{s.band_persistence:.6f}",
                    f"{s.near_cycle_score:.6f}", s.even_steps, s.odd_steps,
                    f"{s.odd_fraction:.6f}",
                ])
        if show_progress:
            print()
        print(f"Wrote {total:,} rows → {out_path}")
    else:
        from collatz.analysis import find_interesting
        results = find_interesting(start, end, metric=metric, top_n=10,
                                   progress=_progress)
        if show_progress:
            print()
        print(f"Top {len(results)} by {metric} in [{start:,}, {end:,}]:")
        print(f"{'n':>12}  {'score':>12}")
        print("-" * 28)
        for n, score in results:
            print(f"{n:>12,}  {score:>12.2f}")


def _cli_graph(
    n: int,
    output: str,
    graph_type: str = "collatz",
    depth: int = 6,
) -> None:
    """Export a Collatz graph to a file (PNG, SVG, or CSV).

    Args:
        n:          Starting positive integer.
        output:     Destination file path.  The extension determines the
                    format: ``.png``, ``.svg``, or ``.csv``.
        graph_type: ``"collatz"`` for the forward directed graph of ``{1..n}``;
                    ``"inverse"`` for the predecessor tree rooted at ``n``.
        depth:      Expansion depth for the inverse tree (ignored for
                    ``graph_type="collatz"``).
    """
    from pathlib import Path
    from collatz.core import sequence
    from collatz.graph_export import (
        build_collatz_graph,
        build_inverse_tree,
        export_csv,
        export_image,
    )

    seq = sequence(n)

    if graph_type == "inverse":
        nodes, edges = build_inverse_tree(n, depth=depth, seq=seq)
        title = f"Inverse Predecessor Tree  —  n = {n:,},  depth = {depth}"
    else:
        nodes, edges = build_collatz_graph(n, seq=seq)
        title = f"Collatz Graph  —  n = {n:,}  ({len(nodes)} nodes)"

    ext = Path(output).suffix.lower()
    if ext == ".csv":
        n_path, e_path = export_csv(nodes, edges, output)
        print(f"Graph: {len(nodes):,} nodes, {len(edges):,} edges")
        print(f"Nodes → {n_path}")
        print(f"Edges → {e_path}")
    elif ext in (".png", ".svg", ".pdf"):
        export_image(nodes, edges, output, title=title)
        print(f"Graph: {len(nodes):,} nodes, {len(edges):,} edges")
        print(f"Saved → {output}")
    else:
        print(
            f"Error: unsupported format '{ext}'.  "
            "Use .csv, .png, .svg, or .pdf.",
            file=sys.stderr,
        )
        sys.exit(1)


# ---------------------------------------------------------------------------
# Argument parser
# ---------------------------------------------------------------------------

def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="collatz-explorer",
        description="Collatz Conjecture Explorer — GUI and CLI tool.",
        epilog=(
            "Examples:\n"
            "  python main.py                          # launch GUI\n"
            "  python main.py --cli 27                 # print stats\n"
            "  python main.py --scan 1 1000            # top-10 by stopping time\n"
            "  python main.py --scan 1 1000 --metric altitude\n"
            "  python main.py --graph 27 --output g.png\n"
            "  python main.py --graph 27 --output g.csv\n"
            "  python main.py --inverse 27 --depth 6 --output t.svg\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--cli",
        metavar="N",
        type=int,
        help=(
            "Print all trajectory statistics for N (stopping time, peak, "
            "altitude, glide, oscillation index, band persistence, "
            "near-cycle score, odd/even step counts).  No GUI is launched."
        ),
    )
    parser.add_argument(
        "--scan",
        metavar=("START", "END"),
        nargs=2,
        type=int,
        help=(
            "Scan [START, END] and print the top-10 starting values ranked "
            "by the chosen --metric."
        ),
    )
    parser.add_argument(
        "--metric",
        default="stopping_time",
        choices=[
            "stopping_time", "altitude", "oscillation_index",
            "band_persistence", "near_cycle_score",
        ],
        help="Metric used for --scan ranking (default: stopping_time).",
    )
    parser.add_argument(
        "--graph",
        metavar="N",
        type=int,
        help=(
            "Export the forward Collatz directed graph for N.  "
            "Nodes are {1…N} (capped at 300; falls back to path-only for "
            "larger N).  Use --output to specify the destination file."
        ),
    )
    parser.add_argument(
        "--inverse",
        metavar="N",
        type=int,
        help=(
            "Export the inverse predecessor tree rooted at N.  "
            "Every node M in the tree satisfies step(M) = parent, so "
            "M's Collatz sequence passes through N on its way to 1.  "
            "Use --depth to control expansion depth."
        ),
    )
    parser.add_argument(
        "--output",
        metavar="FILE",
        help=(
            "Output file for --graph, --inverse, or --scan --full.  "
            "For --graph/--inverse, the format is determined by the extension: "
            ".png (raster image), .svg (vector), .pdf (PDF), "
            ".csv (writes {base}_nodes.csv and {base}_edges.csv).  "
            "For --scan --full, must be a .csv path.  "
            "A default filename is generated when this flag is omitted."
        ),
    )
    parser.add_argument(
        "--full",
        action="store_true",
        help=(
            "With --scan: write all metrics for every n in the range to a CSV "
            "file instead of printing the top-10 ranking.  The output path "
            "defaults to collatz_stats_{start}_{end}.csv; override with --output."
        ),
    )
    parser.add_argument(
        "--depth",
        metavar="D",
        type=int,
        default=6,
        help=(
            "Depth for --inverse tree expansion "
            "(1 = direct predecessors only, default: 6)."
        ),
    )
    return parser


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    """Parse command-line arguments and dispatch to the appropriate mode."""
    parser = _build_parser()
    args = parser.parse_args()

    if args.cli is not None:
        _cli_explore(args.cli)
        sys.exit(0)

    if args.scan is not None:
        start, end = args.scan
        _cli_scan(start, end, metric=args.metric,
                  full=args.full, output=args.output)
        sys.exit(0)

    if args.graph is not None:
        output = args.output or f"collatz_graph_{args.graph}.png"
        _cli_graph(args.graph, output, graph_type="collatz")
        sys.exit(0)

    if args.inverse is not None:
        output = (
            args.output
            or f"collatz_inverse_{args.inverse}_d{args.depth}.png"
        )
        _cli_graph(args.inverse, output, graph_type="inverse",
                   depth=args.depth)
        sys.exit(0)

    # Default: launch GUI
    from gui.app import run
    run()


if __name__ == "__main__":
    main()
