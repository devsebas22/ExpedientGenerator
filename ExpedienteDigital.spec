# -*- mode: python ; coding: utf-8 -*-
"""
Spec de PyInstaller — Expediente Digital
Modo: ONEFILE (un único ExpedienteDigital.exe autocontenido)

Qué incluye este .exe:
  - Python embebido (el cliente NO necesita instalar Python)
  - FastAPI + Uvicorn + todas las dependencias
  - PyMuPDF con sus DLLs nativas (procesamiento de PDF)
  - Frontend completo (HTML + CSS + JS)
  - Sin dependencias de rutas absolutas de desarrollo
"""
from PyInstaller.utils.hooks import collect_all

block_cipher = None

# ── collect_all para paquetes con importaciones dinámicas ────────────────────
# Estos paquetes usan __import__, importlib, o plugins que PyInstaller
# no detecta con análisis estático. collect_all captura TODO: código,
# datos nativos, DLLs y submódulos.
mupdf_d,     mupdf_b,     mupdf_h     = collect_all("pymupdf")
uvicorn_d,   uvicorn_b,   uvicorn_h   = collect_all("uvicorn")
starlette_d, starlette_b, starlette_h = collect_all("starlette")   # FIX: faltaba
anyio_d,     anyio_b,     anyio_h     = collect_all("anyio")
aiofiles_d,  aiofiles_b,  aiofiles_h  = collect_all("aiofiles")
pydantic_d,  pydantic_b,  pydantic_h  = collect_all("pydantic")    # FIX: faltaba

a = Analysis(
    ["launcher.py"],
    pathex=["."],
    binaries=[
        *mupdf_b,
        *uvicorn_b,
        *starlette_b,
        *anyio_b,
        *aiofiles_b,
        *pydantic_b,
    ],
    datas=[
        # ── Archivos estáticos del frontend ───────────────────────────────────
        # Se extraen a _MEIPASS/frontend/ al arrancar el .exe
        # backend/main.py los encuentra vía Path(sys._MEIPASS) / "frontend"
        ("frontend", "frontend"),
        # ── Datos nativos de los paquetes ─────────────────────────────────────
        *mupdf_d,
        *uvicorn_d,
        *starlette_d,
        *anyio_d,
        *aiofiles_d,
        *pydantic_d,
    ],
    hiddenimports=[
        # ── Colecciones dinámicas (ya capturan la mayoría) ────────────────────
        *mupdf_h,
        *uvicorn_h,
        *starlette_h,
        *anyio_h,
        *aiofiles_h,
        *pydantic_h,
        # ── PyMuPDF: alias legacy necesario ───────────────────────────────────
        "fitz",
        "fitz.fitz",
        # ── pydantic v2 core (extensión compilada con importación dinámica) ───
        "pydantic_core",
        "pydantic_core._pydantic_core",
        # ── HTTP / multipart ──────────────────────────────────────────────────
        "h11",
        "h11._connection",
        "h11._events",
        "h11._readers",
        "h11._writers",
        "multipart",
        "multipart.multipart",
        "python_multipart",
        # ── fastapi internals ─────────────────────────────────────────────────
        "fastapi",
        "fastapi.middleware",
        "fastapi.middleware.cors",
        "fastapi.responses",
        "fastapi.staticfiles",
        # ── stdlib usado explícitamente ───────────────────────────────────────
        "email.mime.text",
        "email.mime.multipart",
        "logging.handlers",
        "ctypes",
        "ctypes.wintypes",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Reducir tamaño: paquetes que NO usa la app
        "tkinter",
        "_tkinter",
        "matplotlib",
        "numpy",
        "scipy",
        "PIL",
        "IPython",
        "jupyter",
        "pytest",
        "unittest",
        "doctest",
        "pdb",
        "xml.etree",   # no usado
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# ── EXE onefile ───────────────────────────────────────────────────────────────
# Todo (Python, libs, frontend) queda dentro de un único .exe.
# Al ejecutarse, se autoextrae a %TEMP%\_MEIxxxxxx y arranca desde allí.
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
    upx_exclude=["*.dll", "*.pyd"],   # UPX puede corromper DLLs nativas
    runtime_tmpdir=None,
    console=False,                     # sin ventana de terminal para el usuario
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon="assets/icono.ico",
)
