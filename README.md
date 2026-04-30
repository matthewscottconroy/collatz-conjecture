# Collatz Conjecture Explorer

An interactive Python application for discovering and visualising interesting
behaviour in the Collatz (3x+1) conjecture.

---

## Background

The **Collatz conjecture** states that for any positive integer *n*, repeated
application of the function

```
f(n) = n / 2        if n is even
f(n) = 3 * n + 1    if n is odd
```

eventually reaches 1.  Despite being simple to state, it remains unproven.

This project focuses not on the proof, but on the rich variety of behaviour
exhibited by individual sequences — long trajectories, dramatic peaks,
near-cyclic oscillation, and striking visual patterns.

---

## Features

### GUI tabs

| Tab | Description |
|-----|-------------|
| **Trajectory** | Step-by-step value plot, linear or log scale |
| **Phase Plot** | `seq[k]` vs `seq[k+1]`, optionally on log–log axes |
| **Parity & Rhythm** | Even/odd raster, bit-length walk, odd-step gap histogram |
| **Range Scan** | Bar chart, scatter, heatmap, record holders, trajectory fingerprint |
| **Compare** | Overlay multiple sequences on one canvas |
| **Graph** | Interactive force-directed Collatz graph with drag support |
| **Inverse Tree** | Inverse predecessor tree with adjustable depth |
| **Library** | Curated catalogue of 30+ interesting starting values |

### Statistics panel

Stopping time · peak value · altitude · glide · oscillation index · band
persistence · near-cycle score · odd/even step counts, shown alongside every
trajectory.

### CLI

No GUI required — all major operations are available at the terminal.

---

## Metrics

| Metric | Meaning |
|--------|---------|
| **Stopping time** | Total steps to reach 1 |
| **Peak value** | Maximum value encountered |
| **Altitude** | `peak / n` — how high relative to the start |
| **Glide** | Steps until first drop below `n` |
| **Oscillation index** | Fraction of steps that are local maxima |
| **Band persistence** | Longest fraction spent within a 4× value band (near-cycle hint) |
| **Near-cycle score** | 0–1; 1 = perfectly equal local maxima (cycle-like) |

---

## Requirements

- Python **3.10 or later**

---

## Getting Started

### 0 — Install tkinter (Linux only)

`tkinter` is part of the Python standard library but is packaged separately on
most Linux distributions.  It must be installed **before** creating the virtual
environment because venvs inherit from the system Python.

```bash
# Debian / Ubuntu
sudo apt install python3-tk

# Fedora / RHEL
sudo dnf install python3-tkinter
```

On **macOS** tkinter is included with the python.org installer (Homebrew builds
may need `brew install python-tk`).  On **Windows** it is included with the
standard installer — ensure the *tcl/tk and IDLE* optional feature is ticked.

### 1 — Clone or download the project

```bash
git clone <repository-url> collatz-explorer
cd collatz-explorer
```

Or download and extract the ZIP, then open a terminal in the project folder.

### 2 — Create a virtual environment

```bash
python3 -m venv .venv
```

### 3 — Activate the virtual environment

| Platform | Shell | Command |
|----------|-------|---------|
| Linux / macOS | bash / zsh | `source .venv/bin/activate` |
| Windows | Command Prompt | `.venv\Scripts\activate.bat` |
| Windows | PowerShell | `.venv\Scripts\Activate.ps1` |

Your prompt will show `(.venv)` when the environment is active.

### 4 — Install dependencies

```bash
pip install -r requirements.txt
```

To also install the optional development tools (pytest, coverage):

```bash
pip install -e ".[dev]"
```

### 5 — Run the application

**GUI (default):**

```bash
python main.py
```

**CLI — print trajectory statistics:**

```bash
python main.py --cli 27
```

**CLI — scan a range and rank by a metric:**

```bash
python main.py --scan 1 1000
python main.py --scan 1 1000 --metric altitude
```

**CLI — export a graph:**

```bash
python main.py --graph 27 --output collatz_27.png
python main.py --graph 27 --output collatz_27.svg
python main.py --graph 27 --output collatz_27.csv
```

**CLI — export an inverse predecessor tree:**

```bash
python main.py --inverse 27 --output tree_27.png
python main.py --inverse 27 --depth 8 --output tree_27_deep.svg
python main.py --inverse 27 --depth 4 --output tree_27.csv
```

### 6 — Deactivate the virtual environment

```bash
deactivate
```

---

## Usage

### GUI

1. Type any positive integer in the **Explore** box and press Enter or click
   **Explore** (or double-click a library entry to jump straight to it).
2. Browse the **Library** tree on the left to jump to known interesting values.
3. Use the tabs to switch between views — each tab updates automatically when
   you explore a new number.
4. Click **+ Compare** to queue the current `n` for the **Compare** tab.
5. Use the **Range Scan** tab to analyse a whole range at once — choose from
   stopping-time bar chart, altitude scatter, convergence heatmap, record
   holders, or trajectory fingerprint.  Scans run in the background so the UI
   stays responsive.
6. Use the **Graph** tab for an interactive force-directed layout of the
   Collatz graph.  Nodes can be click-dragged; the physics keeps running.
7. Use the **Inverse Tree** tab to explore which numbers feed into the current
   `n` — adjust depth with the spinbox and click **Rebuild**.

### CLI — trajectory statistics

```bash
# All metrics for a single n:
python main.py --cli 27
python main.py --cli 837799
```

Output includes: stopping time, peak value, altitude, glide, oscillation
index, band persistence, near-cycle score, odd/even step counts.

### CLI — range scan

```bash
# Top-10 by stopping time in [1, 1000]:
python main.py --scan 1 1000

# Available --metric values:
#   stopping_time  altitude  oscillation_index  band_persistence  near_cycle_score
python main.py --scan 1 1000 --metric altitude
python main.py --scan 1 1000 --metric oscillation_index
```

### CLI — graph export

Export the **forward Collatz directed graph** (nodes `{1…n}`, each with an
edge to its Collatz successor) as a PNG, SVG, or CSV:

```bash
python main.py --graph 27 --output collatz_27.png
python main.py --graph 27 --output collatz_27.svg
python main.py --graph 27 --output collatz_27.csv
```

When `--output` is omitted a default filename is generated automatically.

For `n > 300`, the node set falls back to path-only to keep the output
manageable.

Export the **inverse predecessor tree** rooted at `n` (every node `m` in the
tree has `step(m) = parent`, so `m`'s sequence passes through `n` on its way
to 1):

```bash
python main.py --inverse 27 --output tree_27.png
python main.py --inverse 27 --depth 8 --output tree_27_deep.svg
python main.py --inverse 27 --depth 4 --output tree_27.csv
```

The `--depth` flag (default 6) controls how many predecessor levels to expand.

**CSV output** writes two files: `{base}_nodes.csv` (columns: `id`, `type`)
and `{base}_edges.csv` (columns: `source`, `target`), ready to import into
Gephi, Cytoscape, D3.js, or any tool that accepts separate node/edge tables.

### Library API

```python
from collatz.library import by_category, by_tag, find_entry

# All "long trajectory" entries:
for entry in by_category("long_trajectory"):
    print(entry)

# Entries tagged "record":
for entry in by_tag("record"):
    print(f"{entry.n}: {entry.description}")

# Look up a specific n:
for entry in find_entry(837799):
    print(entry.notes)
```

### Programmatic analysis

```python
from collatz import compute_stats, find_interesting, get_predecessors, sequence

# Detailed stats for one number:
stats = compute_stats(27)
print(stats.summary())

# Top 10 by altitude in [1, 10000]:
for n, altitude in find_interesting(1, 10_000, metric="altitude", top_n=10):
    print(f"n={n:,}  altitude={altitude:.1f}×")

# Inverse predecessors (who feeds into 10?):
print(get_predecessors(10))   # [20, 3]
```

### Graph export API

```python
from collatz.graph_export import (
    build_collatz_graph, build_inverse_tree,
    export_image, export_csv,
)

# Forward graph for n=27 → PNG
nodes, edges = build_collatz_graph(27)
export_image(nodes, edges, "collatz_27.png", title="Collatz graph  n=27")

# Inverse tree, depth 5 → CSV (two files: tree_27_nodes.csv, tree_27_edges.csv)
nodes, edges = build_inverse_tree(27, depth=5)
n_file, e_file = export_csv(nodes, edges, "tree_27.csv")
```

---

## Building a Standalone Binary

You can package the application into a self-contained executable using
[PyInstaller](https://pyinstaller.org).  The result runs on any machine of
the same OS and architecture — no Python installation required.

### 1 — Install PyInstaller

```bash
pip install -e ".[build]"
```

Or directly:

```bash
pip install "pyinstaller>=6.0"
```

### 2 — Build

```bash
pyinstaller collatz.spec
```

This produces a **one-directory bundle** in `dist/collatz-explorer/`.

### 3 — Run the binary

| Platform | Command |
|----------|---------|
| Linux / macOS | `./dist/collatz-explorer/collatz-explorer` |
| Windows | `dist\collatz-explorer\collatz-explorer.exe` |

All CLI flags work exactly as with `python main.py`:

```bash
./dist/collatz-explorer/collatz-explorer --cli 27
./dist/collatz-explorer/collatz-explorer --scan 1 1000 --metric altitude
./dist/collatz-explorer/collatz-explorer --graph 27 --output g.png
```

### Single-file mode (optional)

To get a single executable file instead of a directory, open `collatz.spec`
and change the line near the top from:

```python
onefile = False
```

to:

```python
onefile = True
```

Then rebuild with `pyinstaller collatz.spec`.  The output is a single file at
`dist/collatz-explorer` (or `dist/collatz-explorer.exe` on Windows).

> **Note:** Single-file mode is slower to launch because the app must unpack
> itself into a temporary directory on every run.  The one-directory mode
> (`onefile = False`) starts instantly and is recommended for everyday use.

### Platform notes

**Linux** — tkinter must be installed system-wide *before* building (the same
requirement as for running from source; see Step 0 of Getting Started above).
PyInstaller bundles everything else.

**macOS** — build on the target macOS version.  Apple Silicon and Intel
produce separate binaries; no universal binary support is provided by default.

**Windows** — the build produces a `.exe`.  [UPX](https://upx.github.io/) is
used automatically if installed, reducing the binary size by ~30%.

### Clean build artefacts

```bash
rm -rf build/ dist/ *.spec.bak
```

---

## Running Tests

```bash
pytest                           # All tests
pytest --cov=collatz             # With coverage report
pytest tests/test_core.py        # One module only
```

All tests are in `tests/` and use **pytest**.  The suite covers:

| File | What is tested |
|------|----------------|
| `test_core.py` | `step`, `sequence`, `sequence_iter`, `total_stopping_time`, `is_power_of_two`, `get_predecessors`, `max_iter` boundary, recursion-depth regression, cross-function consistency |
| `test_analysis.py` | All metrics, `TrajectoryStats`, `find_interesting`, edge cases for n=1/2/power-of-two |
| `test_library.py` | Library integrity (pre-computed stats verified against live computation), accessor functions |
| `test_visualization.py` | Smoke tests for every plot function, `seq` parameter consistency, axes properties |
| `test_graph_export.py` | `build_collatz_graph`, `build_inverse_tree`, `export_csv`, `export_image`, `_force_layout` |
| `test_cli.py` | All CLI entry points (`--cli`, `--scan`, `--graph`, `--inverse`), argparse dispatch, file creation |
| `test_api.py` | Public `collatz` package API: `__all__` completeness, every exported symbol, `__version__`, sub-module accessibility |

---

## Project Structure

```
collatz-explorer/
├── main.py                  Entry point (GUI + CLI)
├── collatz/
│   ├── __init__.py          Public API (re-exports + __version__)
│   ├── core.py              Sequence computation (step, sequence, stopping time,
│   │                          get_predecessors)
│   ├── analysis.py          Statistical metrics and TrajectoryStats
│   ├── library.py           Curated catalogue of interesting starting values
│   ├── visualization.py     Matplotlib plot helpers (trajectory, phase, parity,
│   │                          range, comparative)
│   └── graph_export.py      Graph building and export (PNG, SVG, CSV)
├── gui/
│   ├── __init__.py
│   ├── app.py               Tkinter + matplotlib GUI application
│   ├── theme.py             Centralised Catppuccin Mocha colour palette
│   ├── graph_tab.py         Interactive force-directed Collatz graph tab
│   ├── parity_tab.py        Parity raster / bit-length / odd-step histogram tab
│   └── inverse_tree_tab.py  Inverse predecessor tree tab
├── tests/
│   ├── test_core.py
│   ├── test_analysis.py
│   ├── test_library.py
│   ├── test_visualization.py
│   ├── test_graph_export.py
│   ├── test_cli.py
│   └── test_api.py
├── collatz.spec             PyInstaller build spec
├── pyproject.toml
└── requirements.txt
```

---

## Notable Library Entries

| n | Name | Stopping time | Peak | Altitude |
|---|------|--------------|------|----------|
| 27 | The Celebrity | 111 | 9,232 | 342× |
| 703 | Triple Digits Champion | 170 | 250,504 | 356× |
| 837,799 | Million Milestone | 524 | 2,974,984,576 | 3,551× |
| 4 | Trivial Cycle Start | 2 | 4 | 1× |
| 1,024 | 2¹⁰ | 10 | 1,024 | 1× |

---

## Interesting Things to Try

- Compare 27 and 703 on the **Compare** tab — both have long trajectories but
  very different shapes.
- Scan [1, 1000] by *altitude* to find the highest-climbing numbers.
- Switch to **Log Scale** for n=837799 to see its full structure without the
  peak dwarfing everything else.
- Look at the **Phase Portrait** for n=27 to see the characteristic 3n+1
  fan-out and ÷2 collapse structure.
- Open the **Parity & Rhythm** tab for n=27 to see the even/odd parity raster
  and the random-walk interpretation of the bit-length.
- Drag nodes around in the **Graph** tab and watch the physics settle.
- Grow the **Inverse Tree** to depth 8 to see how many predecessors exist at
  each level.
- Export the inverse tree for n=1 to depth 10 as CSV and load it into Gephi to
  visualise the full structure at scale.

---

## License

MIT
