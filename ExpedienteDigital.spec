# -*- mode: python ; coding: utf-8 -*-
"""
Spec de PyInstaller — Expediente Digital
Modo: ONEFILE (un único ExpedienteDigital.exe autocontenido)

Qué incluye este .exe:
  - Python embebido (el cliente NO necesita instalar Python)
  - FastAPI + Uvicorn + todas las dependencias
  - PyMuPDF con sus DLLs nativas (procesamiento de PDF)
  - Pillow para conversión de imágenes a PDF
  - python-docx + reportlab para conversión de Word a PDF
  - Frontend completo (HTML + CSS + JS)
  - Sin dependencias de rutas absolutas de desarrollo
"""
from PyInstaller.utils.hooks import collect_all

block_cipher = None

# ── collect_all para paquetes con importaciones dinámicas ────────────────────
mupdf_d,      mupdf_b,      mupdf_h      = collect_all("pymupdf")
uvicorn_d,    uvicorn_b,    uvicorn_h    = collect_all("uvicorn")
starlette_d,  starlette_b,  starlette_h  = collect_all("starlette")
anyio_d,      anyio_b,      anyio_h      = collect_all("anyio")
aiofiles_d,   aiofiles_b,   aiofiles_h   = collect_all("aiofiles")
pydantic_d,   pydantic_b,   pydantic_h   = collect_all("pydantic")
pil_d,        pil_b,        pil_h        = collect_all("PIL")          # Pillow (imágenes)
reportlab_d,  reportlab_b,  reportlab_h  = collect_all("reportlab")   # PDF desde Word
docx_d,       docx_b,       docx_h       = collect_all("docx")        # python-docx

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
        *pil_b,
        *reportlab_b,
        *docx_b,
    ],
    datas=[
        # ── Archivos estáticos del frontend ───────────────────────────────────
        ("frontend", "frontend"),
        # ── Datos nativos de los paquetes ─────────────────────────────────────
        *mupdf_d,
        *uvicorn_d,
        *starlette_d,
        *anyio_d,
        *aiofiles_d,
        *pydantic_d,
        *pil_d,
        *reportlab_d,
        *docx_d,
    ],
    hiddenimports=[
        # ── Colecciones dinámicas ─────────────────────────────────────────────
        *mupdf_h,
        *uvicorn_h,
        *starlette_h,
        *anyio_h,
        *aiofiles_h,
        *pydantic_h,
        *pil_h,
        *reportlab_h,
        *docx_h,
        # ── PyMuPDF: alias legacy ─────────────────────────────────────────────
        "fitz",
        "fitz.fitz",
        # ── pydantic v2 core ──────────────────────────────────────────────────
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
        # ── Pillow: plugins de formato de imagen (carga dinámica) ─────────────
        "PIL",
        "PIL.Image",
        "PIL.JpegImagePlugin",
        "PIL.PngImagePlugin",
        "PIL.BmpImagePlugin",
        "PIL.GifImagePlugin",
        "PIL.TiffImagePlugin",
        "PIL.WebPImagePlugin",
        "PIL.IcoImagePlugin",
        "PIL.ImageFile",
        "PIL.ImageMode",
        # ── reportlab: subpaquetes con registro dinámico ──────────────────────
        "reportlab.graphics",
        "reportlab.lib",
        "reportlab.lib.colors",
        "reportlab.lib.pagesizes",
        "reportlab.lib.styles",
        "reportlab.lib.units",
        "reportlab.pdfgen",
        "reportlab.pdfgen.canvas",
        "reportlab.platypus",
        "reportlab.platypus.paragraph",
        # ── python-docx: requiere lxml para XML ──────────────────────────────
        "docx",
        "docx.document",
        "docx.opc.pkgreader",
        "lxml",
        "lxml.etree",
        # ── stdlib ────────────────────────────────────────────────────────────
        "email.mime.text",
        "email.mime.multipart",
        "logging.handlers",
        "ctypes",
        "ctypes.wintypes",
        "xml.etree.ElementTree",
        "zipfile",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Paquetes que la app definitivamente no usa
        "tkinter",
        "_tkinter",
        "matplotlib",
        "numpy",
        "scipy",
        "IPython",
        "jupyter",
        "pytest",
        "unittest",
        "doctest",
        "pdb",
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# ── EXE onefile ───────────────────────────────────────────────────────────────
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="ExpedienteDigital_app",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=["*.dll", "*.pyd"],   # UPX puede corromper DLLs nativas
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon="assets/icono.ico",
)
