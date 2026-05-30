# -*- mode: python ; coding: utf-8 -*-
"""
Spec de PyInstaller — Launcher ligero de Expediente Digital
Entry point: launcher_main.py  (solo stdlib — sin FastAPI, uvicorn, PyMuPDF, etc.)

Flujo del launcher:
  1. Si la app ya está corriendo → abre el navegador y sale
  2. Primera vez: copia ExpedienteDigital_app.exe a AppData\Local\ExpedienteDigital\
  3. Comprueba actualización → descarga y reemplaza app.exe (sin DLL locks)
  4. Lanza ExpedienteDigital_app.exe desacoplado y sale

Tamaño objetivo: ~7-8 MB  (Python embebido + stdlib)
"""

block_cipher = None

a = Analysis(
    ["launcher_main.py"],
    pathex=["."],
    binaries=[],
    datas=[],
    hiddenimports=[
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
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Excluir TODO lo que no es stdlib para mantener el tamaño mínimo
        "tkinter", "_tkinter",
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
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="ExpedienteDigital",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],      # no hay DLLs nativas — UPX puede comprimir libremente
    runtime_tmpdir=None,
    console=False,       # sin ventana de consola (windowed)
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon="assets/icono.ico",
)
