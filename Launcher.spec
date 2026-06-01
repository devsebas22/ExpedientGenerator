# -*- mode: python ; coding: utf-8 -*-
"""
Spec de PyInstaller — Launcher de Expediente Digital (onedir)
Entry point: launcher_with_splash.py  (muestra splash + delega a launcher_main)

Cambios vs. versión anterior:
  - onedir en vez de onefile: sin descompresión en Temp → apertura instantánea
  - tkinter incluido: para el splash screen
  - launcher_with_splash.py como entry point

Salida: dist/launcher/   (carpeta con ExpedienteDigital.exe + dependencias)
El instalador copia dist/launcher/* a {app}\ directamente.

Tamaño objetivo: ~10-12 MB con tkinter
"""

block_cipher = None

a = Analysis(
    ["launcher_with_splash.py"],
    pathex=["."],
    binaries=[],
    datas=[],
    hiddenimports=[
        # launcher_main es importado por launcher_with_splash
        "launcher_main",
        # stdlib que PyInstaller a veces no detecta automáticamente
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
        "datetime",
        "traceback",
        "time",
        # tkinter para el splash screen
        "tkinter",
        "tkinter.ttk",
        "_tkinter",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Excluir TODO lo que no es stdlib/tkinter para mantener el tamaño mínimo
        "fastapi", "uvicorn", "starlette", "anyio", "aiofiles",
        "pydantic", "pydantic_core",
        "PIL", "Pillow", "pymupdf", "fitz",
        "reportlab", "docx", "lxml",
        "h11", "multipart", "python_multipart",
        "httpx", "httpcore", "requests",
        "numpy", "scipy", "matplotlib",
        "IPython", "jupyter",
        "pytest", "unittest", "doctest", "pdb",
        "concurrent.futures",
        "multiprocessing",
        "asyncio",
        "xmlrpc",
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,    # binaries van al COLLECT (onedir)
    name="ExpedienteDigital",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    console=False,            # sin ventana de consola (windowed)
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon="assets/icono.ico",
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="launcher",          # → dist/launcher/
)
