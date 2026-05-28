# -*- mode: python ; coding: utf-8 -*-
"""
Spec de PyInstaller — Launcher de Expediente Digital
Solo stdlib → binario pequeño (~8 MB).
"""

a = Analysis(
    ["launcher_main.py"],
    pathex=["."],
    binaries=[],
    datas=[],
    hiddenimports=[
        "ctypes",
        "ctypes.wintypes",
        "urllib.request",
        "urllib.parse",
        "urllib.error",
        "json",
        "shutil",
        "subprocess",
        "webbrowser",
        "pathlib",
        "threading",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # excluir todo lo que no es stdlib
        "tkinter", "_tkinter",
        "fastapi", "uvicorn", "starlette", "anyio", "aiofiles",
        "pydantic", "pydantic_core",
        "PIL", "pymupdf", "fitz",
        "reportlab", "docx", "lxml",
        "h11", "multipart",
        "numpy", "scipy", "matplotlib",
        "IPython", "jupyter",
        "pytest", "unittest", "doctest", "pdb",
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=None)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="ExpedienteDigital",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon="assets/icono.ico",
)
