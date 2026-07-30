# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec for the Wealth VN backend sidecar.
#
# Builds a single-file executable (`wealth-backend`) that embeds the FastAPI
# app, all API/service/job modules, and the required third-party packages.
# The resulting binary is renamed to `wealth-backend-x86_64-pc-windows-msvc.exe`
# by scripts/build_sidecar.ps1 so Tauri can register it as a sidecar.

import os
from PyInstaller.utils.hooks import collect_submodules, collect_data_files, collect_dynamic_libs

# Absolute path to the backend source directory (where this spec lives).
BACKEND_DIR = os.path.abspath(SPECPATH)

# --- Hidden imports ---------------------------------------------------------
# Collect every submodule from our own packages so PyInstaller does not miss
# dynamically imported routers / services / jobs.
hiddenimports = []
hiddenimports += collect_submodules('api')
hiddenimports += collect_submodules('services')
hiddenimports += collect_submodules('jobs')
hiddenimports += collect_submodules('common')

# Third-party packages that are imported dynamically or via string paths.
hiddenimports += [
    'sqlite_vec',
    'uvicorn',
    'uvicorn.logging',
    'uvicorn.protocols',
    'uvicorn.protocols.http',
    'uvicorn.protocols.http.auto',
    'uvicorn.protocols.websockets',
    'uvicorn.protocols.websockets.auto',
    'uvicorn.lifespan',
    'uvicorn.lifespan.on',
    'fastapi',
    'sqlmodel',
    'apscheduler',
    'apscheduler.schedulers.background',
    'tenacity',
    'feedparser',
    'bs4',
    'openpyxl',
    'google.genai',
    'alembic',
    'pydantic_settings',
    'pydantic',
    'vnstock',
    'certifi',
]

# --- Binary extensions ------------------------------------------------------
# sqlite-vec ships a native shared library that must be bundled with the
# package or sqlite_vec.load() will fail with "The specified module could not
# be found." in the PyInstaller one-file executable.
binaries = []
binaries += collect_dynamic_libs('sqlite_vec')

# --- Data files -------------------------------------------------------------
# Ship the Python source modules alongside the binary so importlib can load
# them at runtime. On Windows the separator is ';'.
datas = []
datas += collect_data_files('sqlite_vec')
datas += collect_data_files('certifi')
datas += collect_data_files('api', include_py_files=True)
datas += collect_data_files('services', include_py_files=True)
datas += collect_data_files('jobs', include_py_files=True)

# Explicitly include the top-level backend modules.
for mod in ('main.py', 'models.py', 'schemas.py', 'config.py', 'database.py'):
    datas.append((os.path.join(BACKEND_DIR, mod), '.'))

# Include the runtime hook that configures the data directory.
datas.append((os.path.join(BACKEND_DIR, 'runtime_hook.py'), '.'))

# --- Excludes ---------------------------------------------------------------
# Test-only dependencies should not be bundled into the sidecar.
excludes = [
    'pytest',
    'coverage',
    'mypy',
    'pytest_cov',
    '_pytest',
]

# --- Analysis ---------------------------------------------------------------
a = Analysis(
    [os.path.join(BACKEND_DIR, 'main.py')],
    pathex=[BACKEND_DIR],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[os.path.join(BACKEND_DIR, 'runtime_hook.py')],
    excludes=excludes,
    noarchive=False,
)

pyz = PYZ(a.pure)

# --- Single-file executable -------------------------------------------------
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='wealth-backend',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,  # keep stdout/stderr for Tauri to capture
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
