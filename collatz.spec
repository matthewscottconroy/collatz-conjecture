# -*- mode: python ; coding: utf-8 -*-
#
# PyInstaller spec file for Collatz Conjecture Explorer.
#
# Build commands
# --------------
# One-directory bundle (faster startup, recommended):
#   pyinstaller collatz.spec
#
# The output lands in dist/collatz-explorer/.
# Run it with:
#   dist/collatz-explorer/collatz-explorer          (Linux / macOS)
#   dist\collatz-explorer\collatz-explorer.exe      (Windows)
#
# To produce a single-file executable instead, change the two
# `onefile = False` lines below to `onefile = True`.
#
# See README.md § "Building a Standalone Binary" for full details.

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

onefile = False   # change to True for --onefile mode

# matplotlib ships font and style-sheet data that must travel with the binary.
mpl_datas = collect_data_files("matplotlib")

a = Analysis(
    ["main.py"],
    pathex=["."],
    binaries=[],
    datas=mpl_datas,
    hiddenimports=[
        # --- matplotlib backends ---
        # TkAgg is selected at runtime via matplotlib.use("TkAgg"); PyInstaller
        # cannot detect it from a static import scan.
        "matplotlib.backends.backend_tkagg",
        "matplotlib.backends.backend_agg",
        "matplotlib.backends._backend_tk",
        # SVG and PDF are chosen implicitly by file extension in plt.savefig(),
        # not via matplotlib.use(), so PyInstaller's backend scanner misses them.
        "matplotlib.backends.backend_svg",
        "matplotlib.backends.backend_pdf",
        # PIL/Pillow is an optional matplotlib dependency; include it if present
        # so that PNG save works without a separate install.
        "PIL",
        "PIL.Image",
        # --- our packages ---
        # Several submodules are imported inside functions (deferred imports),
        # so they won't be found by the dependency walker.
        "collatz",
        "collatz.core",
        "collatz.analysis",
        "collatz.library",
        "collatz.visualization",
        "collatz.graph_export",
        "gui",
        "gui.app",
        "gui.theme",
        "gui.graph_tab",
        "gui.parity_tab",
        "gui.inverse_tree_tab",
        # --- tkinter ---
        # tkinter is a C extension; list the submodules explicitly to be safe.
        "tkinter",
        "tkinter.ttk",
        "tkinter.messagebox",
        "tkinter.filedialog",
        "tkinter.colorchooser",
        "_tkinter",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Strip test infrastructure — not needed at runtime.
        "pytest",
        "pytest_cov",
        "coverage",
    ],
    noarchive=False,
)

pyz = PYZ(a.pure)

if onefile:
    # ── Single-file mode ────────────────────────────────────────────────────
    # Everything is compressed into one executable.  Startup is slower because
    # the app must unpack to a temp directory on each launch.
    exe = EXE(
        pyz,
        a.scripts,
        a.binaries,
        a.datas,
        name="collatz-explorer",
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=True,
        upx_exclude=[],
        # console=True keeps stdout/stderr alive for the CLI modes.
        # On Windows this opens a terminal window alongside the GUI; that is
        # intentional so --cli / --scan / --graph output remains visible.
        console=True,
        disable_windowed_traceback=False,
        argv_emulation=False,
        target_arch=None,
        codesign_identity=None,
        entitlements_file=None,
    )
else:
    # ── One-directory mode (default) ────────────────────────────────────────
    exe = EXE(
        pyz,
        a.scripts,
        [],
        exclude_binaries=True,
        name="collatz-explorer",
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=True,
        console=True,
        disable_windowed_traceback=False,
        argv_emulation=False,
        target_arch=None,
        codesign_identity=None,
        entitlements_file=None,
    )

    coll = COLLECT(
        exe,
        a.binaries,
        a.zipfiles,
        a.datas,
        strip=False,
        upx=True,
        upx_exclude=[],
        name="collatz-explorer",
    )
