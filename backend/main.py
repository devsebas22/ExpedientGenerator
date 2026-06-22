"""
Expediente Digital — API principal (FastAPI)

Flujo de archivos temporales:
    POST /api/session          → crea temp/session_<uuid>/
    POST /api/upload           → guarda temp/session_<uuid>/<file_uuid>.pdf
    POST /api/process          → procesa archivos y, en try/finally, elimina
                                  temp/session_<uuid>/ completa
    DELETE /api/session/<id>   → limpieza manual anticipada
"""

import asyncio
import hashlib
import json
import logging
import os
import platform
import re
import shutil
import subprocess
import sys
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import aiofiles
import requests as _requests
from fastapi import FastAPI, File, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .models import (
    CountRequest, FileInfo, FolderRequest, FolioConfig, ProcessRequest,
    AppConfigRequest, CreateExpedienteRequest, RenameExpedienteRequest,
    UpdateOrdenRequest, UpdateConfigFolioRequest, GenerarExpedienteRequest,
    ExpedienteConfigFolio,
)
from .pdf_processor import (
    get_page_count, analyze_pdf_file, merge_and_foliate, natural_sort_key,
    convert_image_to_pdf, convert_docx_to_pdf,
)
from .session_manager import SessionManager

# ── Versión y servidor de licencias ───────────────────────────────────────────
_LICENSE_SERVER = "https://expediente-licencias-production.up.railway.app"
import time as _time


def _read_version_actual() -> str:
    """Lee la versión instalada del version.txt escrito por el launcher."""
    try:
        _local = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
        ver_file = Path(_local) / "ExpedienteDigital" / "version.txt"
        if ver_file.exists():
            return ver_file.read_text(encoding="utf-8").strip()
    except Exception:
        pass
    return "1.1.9"  # fallback para modo dev o primera ejecución


def _get_hardware_id() -> str:
    mac = ':'.join(['{:02x}'.format((uuid.getnode() >> e) & 0xff) for e in range(0, 48, 8)][::-1])
    raw = f"{mac}-{platform.processor()}-{platform.system()}{platform.version()}"
    return hashlib.sha256(raw.encode()).hexdigest()[:32]


_nombres_lock = threading.Lock()


def _nombres_path() -> Path:
    """Ruta al registro local de nombres usados hoy."""
    return _BASE / "nombres_usados.json"


def _check_and_register_nombre(nombre: str) -> tuple[int, bool]:
    """
    Comprueba cuántas veces se usó 'nombre' hoy y lo registra si el límite no se alcanzó.
    Retorna (count_antes, registrado).
    - count_antes < 2: incrementa el contador local y retorna (count_antes, True)
    - count_antes >= 2: no modifica nada y retorna (count_antes, False)
    """
    if not nombre:
        return 0, True

    today = datetime.now().strftime("%Y-%m-%d")
    path  = _nombres_path()

    with _nombres_lock:
        try:
            if path.exists():
                data = json.loads(path.read_text(encoding="utf-8"))
                if data.get("fecha") != today:
                    data = {"fecha": today, "nombres": {}}
            else:
                data = {"fecha": today, "nombres": {}}
        except Exception:
            data = {"fecha": today, "nombres": {}}

        count = data["nombres"].get(nombre, 0)

        if count < 2:
            data["nombres"][nombre] = count + 1
            try:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(
                    json.dumps(data, ensure_ascii=False, indent=2),
                    encoding="utf-8",
                )
            except Exception as exc:
                logger.warning("[nombres] no se pudo guardar registro local: %s", exc)
            return count, True
        else:
            return count, False


def _registrar_expediente(output_path: str, nombre_expediente: str = "", paginas_procesadas: int = 0, tiempo_generacion: float = 0.0) -> tuple[bool, int]:
    """
    Registra el expediente en el servidor ANTES de entregarlo al usuario.
    Retorna (ok, total_mes). Si falla, retorna (False, 0).
    """
    try:
        with open(output_path, "rb") as f:
            content = f.read()
        ts_bytes    = str(_time.time()).encode()
        hash_exp    = hashlib.sha256(content + ts_bytes).hexdigest()
        hardware_id = _get_hardware_id()
        resp = _requests.post(
            f"{_LICENSE_SERVER}/api/expediente/registrar",
            json={
                "hardware_id":        hardware_id,
                "hash_expediente":    hash_exp,
                "nombre_expediente":  nombre_expediente,
                "paginas_procesadas": paginas_procesadas,
                "tiempo_generacion":  tiempo_generacion,
            },
            timeout=10,
        )
        data = resp.json()
        return data.get("ok", False), data.get("total_mes", 0)
    except Exception as exc:
        logger.error("[expediente] fallo al registrar: %s", exc)
        return False, 0

# ── Resolución de rutas (dev vs. frozen) ──────────────────────────────────────
def _base_dir() -> Path:
    """Directorio de datos de usuario.
    - Frozen (.exe): %LOCALAPPDATA%\\ExpedienteDigital  (nunca junto al .exe)
    - Dev:           raíz del proyecto
    """
    if getattr(sys, "frozen", False):
        local_app = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
        return Path(local_app) / "ExpedienteDigital"
    return Path(__file__).parent.parent


def _frontend_dir() -> Path:
    """Directorio de archivos estáticos: _MEIPASS/frontend en frozen, /frontend en dev."""
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS) / "frontend"
    return Path(__file__).parent.parent / "frontend"


# ── Rutas base ─────────────────────────────────────────────────────────────────
_BASE      = _base_dir()
TEMP_DIR   = _BASE / "temp"
OUTPUT_DIR = _BASE / "expedientes_generados"
LOG_DIR    = _BASE / "logs"

for _d in (TEMP_DIR, OUTPUT_DIR, LOG_DIR):
    _d.mkdir(exist_ok=True)

# ── Logging ────────────────────────────────────────────────────────────────────
def _setup_logging(log_dir: Path) -> None:
    """
    Configura el logging de forma compatible con PyInstaller frozen mode.

    Por qué NO usar logging.basicConfig ni logging.config.dictConfig:
    - basicConfig es no-op si algún import ya tocó el root logger antes.
    - dictConfig resuelve clases por string ("uvicorn.logging.DefaultFormatter")
      usando importlib, que falla en frozen mode aunque el módulo esté bundled.

    Esta función construye los handlers directamente con objetos Python puros,
    sin ninguna resolución de nombres por string, lo que funciona siempre.
    """
    root = logging.getLogger()

    # No agregar handlers duplicados si alguien llama esto dos veces
    if root.handlers:
        root.handlers.clear()

    root.setLevel(logging.INFO)
    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")

    # Handler de archivo — falla de forma silenciosa si no tiene permisos
    try:
        log_dir.mkdir(parents=True, exist_ok=True)
        fh = logging.FileHandler(log_dir / "expediente.log", encoding="utf-8")
        fh.setFormatter(fmt)
        root.addHandler(fh)
    except Exception as exc:
        print(f"[logging] No se pudo crear log file: {exc}", file=sys.stderr)

    # Handler de consola — siempre presente (útil en dev y en .exe con console=True)
    sh = logging.StreamHandler(sys.stderr)
    sh.setFormatter(fmt)
    root.addHandler(sh)

    # Silenciar los loggers de uvicorn al nivel WARNING para no saturar el log.
    # Como no llamamos logging.config.dictConfig, uvicorn no tiene formateadores
    # propios — sus mensajes llegan al root logger y usan nuestro formato.
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        uv_log = logging.getLogger(name)
        uv_log.setLevel(logging.WARNING)
        uv_log.propagate = True


_setup_logging(LOG_DIR)
logger = logging.getLogger(__name__)

# ── Gestión de sesiones (singleton) ───────────────────────────────────────────
sessions = SessionManager(TEMP_DIR)

# ── Estado en memoria ──────────────────────────────────────────────────────────
uploaded_files: Dict[str, FileInfo] = {}   # {file_id: FileInfo}
tasks: Dict[str, dict]              = {}   # {task_id: dict}

executor = ThreadPoolExecutor(max_workers=2)


# ── Lifespan: limpieza de sesiones obsoletas al arrancar ──────────────────────
@asynccontextmanager
async def lifespan(_app: FastAPI):
    removed = sessions.cleanup_stale(max_age_hours=24)
    if removed:
        logger.info("[inicio] %d sesión(es) obsoleta(s) eliminada(s)", removed)
    yield
    # En shutdown no hay nada especial que hacer


# ── FastAPI ────────────────────────────────────────────────────────────────────
app = FastAPI(title="Expediente Digital", version=_read_version_actual(), lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

FRONTEND = _frontend_dir()
if FRONTEND.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND)), name="static")


@app.get("/")
async def root():
    from fastapi.responses import HTMLResponse
    html = (FRONTEND / "index.html").read_text(encoding="utf-8")
    return HTMLResponse(content=html, headers={"Cache-Control": "no-cache"})


# ═══════════════════════════════════════════════════════════════════════════════
# Sesiones
# ═══════════════════════════════════════════════════════════════════════════════

@app.post("/api/session", status_code=201)
async def create_session():
    """
    Crea una carpeta temporal aislada para una tanda de uploads.
    El frontend llama a este endpoint antes de subir archivos.
    """
    sid = sessions.create()
    logger.info("[session] nueva sesión: %s", sid)
    return {"session_id": sid}


@app.delete("/api/session/{session_id}")
async def delete_session(session_id: str):
    """Limpieza manual anticipada de una sesión y sus archivos temporales."""
    if not sessions.exists(session_id):
        raise HTTPException(404, "Sesión no encontrada o ya eliminada")

    # Quitar registros de memoria
    to_remove = [
        fid for fid, info in uploaded_files.items()
        if info.session_id == session_id
    ]
    for fid in to_remove:
        uploaded_files.pop(fid, None)

    sessions.cleanup(session_id)
    logger.info("[session] eliminación manual: %s (%d archivo(s))", session_id, len(to_remove))
    return {"status": "deleted", "files_removed": len(to_remove)}


# ═══════════════════════════════════════════════════════════════════════════════
# Upload
# ═══════════════════════════════════════════════════════════════════════════════

_IMAGE_EXT = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff", ".webp"}
_WORD_EXT  = {".docx", ".doc"}
_ALL_EXT   = {".pdf"} | _IMAGE_EXT | _WORD_EXT


@app.post("/api/upload")
async def upload_file(
    file: UploadFile = File(...),
    session_id: Optional[str] = Query(None, description="ID de sesión temporal"),
):
    """
    Recibe PDF, imagen o Word y lo convierte a PDF si hace falta.
    Guarda el resultado en temp/session_<id>/<uuid>.pdf.
    """
    ext = Path(file.filename).suffix.lower()
    if ext not in _ALL_EXT:
        raise HTTPException(
            400,
            f"Tipo de archivo no compatible: {file.filename}. "
            "Soportados: PDF, JPEG, PNG y DOCX.",
        )

    if not session_id or not sessions.exists(session_id):
        session_id = sessions.create()
        logger.debug("[upload] sesión creada automáticamente: %s", session_id)

    file_id   = str(uuid.uuid4())
    orig_path = sessions.file_path(session_id, f"{file_id}{ext}")
    pdf_path  = sessions.file_path(session_id, f"{file_id}.pdf")

    try:
        # 1. Guardar el archivo original
        async with aiofiles.open(str(orig_path), "wb") as fh:
            while chunk := await file.read(1024 * 1024):
                await fh.write(chunk)

        # 2. Convertir si no es PDF
        if ext in _IMAGE_EXT:
            try:
                convert_image_to_pdf(str(orig_path), str(pdf_path))
            finally:
                if orig_path.exists():
                    orig_path.unlink()

        elif ext in _WORD_EXT:
            ok = convert_docx_to_pdf(str(orig_path), str(pdf_path))
            if orig_path.exists():
                orig_path.unlink()
            if not ok:
                info = FileInfo(
                    id=file_id, name=file.filename,
                    size=0, pages=-1, path="",
                    session_id=session_id,
                    error="No se pudo convertir el archivo Word. Por favor conviértalo a PDF manualmente.",
                )
                return info

        else:
            # PDF: orig_path ya tiene extensión .pdf, son la misma ruta
            pdf_path = orig_path

        # 3. Analizar el PDF resultante
        pages, error_msg = analyze_pdf_file(str(pdf_path))

        info = FileInfo(
            id         = file_id,
            name       = file.filename,
            size       = pdf_path.stat().st_size if pdf_path.exists() else 0,
            pages      = pages,
            path       = str(pdf_path) if pdf_path.exists() else "",
            session_id = session_id,
            error      = error_msg,
        )
        if pages > 0:
            uploaded_files[file_id] = info
        logger.info(
            "[upload] '%s' → sesión %.8s… | %d págs. | %.1f MB",
            file.filename, session_id, pages,
            (pdf_path.stat().st_size if pdf_path.exists() else 0) / 1_048_576,
        )
        return info

    except HTTPException:
        raise
    except Exception as exc:
        for p in (orig_path, pdf_path):
            if p.exists():
                p.unlink()
        logger.error("[upload] error subiendo '%s': %s", file.filename, exc)
        raise HTTPException(500, str(exc))


# ═══════════════════════════════════════════════════════════════════════════════
# Contador de páginas (sin I/O — O(n) sobre datos en memoria)
# ═══════════════════════════════════════════════════════════════════════════════

@app.post("/api/count-pages")
async def count_pages(request: CountRequest):
    """
    Devuelve conteos por archivo y total.
    Los conteos ya están en memoria desde el upload, sin I/O adicional.
    Si alguno falló (pages == -1), reintenta la lectura.
    """
    file_results = []
    total = 0

    for fid in request.file_ids:
        if fid not in uploaded_files:
            file_results.append({"id": fid, "name": "—", "pages": -1,
                                  "error": "ID no encontrado"})
            continue

        info  = uploaded_files[fid]
        pages = info.pages

        # Reintento si la lectura inicial falló y el archivo todavía existe
        if pages == -1 and info.path and Path(info.path).exists():
            pages = get_page_count(info.path)
            uploaded_files[fid] = info.model_copy(update={"pages": pages})

        file_results.append({"id": fid, "name": info.name,
                              "pages": pages, "error": info.error})
        if pages > 0:
            total += pages

    return {"total_pages": total, "files": file_results}


# ═══════════════════════════════════════════════════════════════════════════════
# Carga desde carpeta local
# ═══════════════════════════════════════════════════════════════════════════════

@app.post("/api/load-folder")
async def load_folder(request: FolderRequest):
    """
    Copia todos los PDFs de una carpeta local a una nueva sesión temporal.
    Devuelve {session_id, files} para que el frontend sincronice su estado.
    """
    folder = Path(request.path.strip())
    if not folder.exists():
        raise HTTPException(404, f"Carpeta no encontrada: {folder}")
    if not folder.is_dir():
        raise HTTPException(400, "La ruta no es una carpeta")

    pdfs = sorted(
        {p for p in folder.iterdir() if p.suffix.lower() == ".pdf"},
        key=lambda p: natural_sort_key(p.name),
    )
    if not pdfs:
        raise HTTPException(404, "No se encontraron PDFs en la carpeta")

    # Crear sesión dedicada para esta carga de carpeta
    session_id = sessions.create()
    logger.info("[folder] cargando %d PDFs desde '%s' → sesión %.8s…",
                len(pdfs), folder, session_id)

    results: List[FileInfo] = []
    for pdf in pdfs:
        file_id   = str(uuid.uuid4())
        file_path = sessions.file_path(session_id, f"{file_id}.pdf")
        try:
            shutil.copy2(str(pdf), str(file_path))
            pages = get_page_count(str(file_path))
            info  = FileInfo(
                id         = file_id,
                name       = pdf.name,
                size       = file_path.stat().st_size,
                pages      = pages,
                path       = str(file_path),
                session_id = session_id,
            )
            uploaded_files[file_id] = info
            results.append(info)
            logger.debug("[folder] '%s' → %d págs.", pdf.name, pages)
        except Exception as exc:
            logger.error("[folder] error cargando '%s': %s", pdf.name, exc)
            results.append(FileInfo(
                id=str(uuid.uuid4()), name=pdf.name,
                size=0, pages=-1, path="",
                session_id=session_id, error=str(exc),
            ))

    logger.info("[folder] sesión %.8s… lista — %d archivo(s)", session_id, len(results))
    return {"session_id": session_id, "files": results}


# ═══════════════════════════════════════════════════════════════════════════════
# Procesamiento (merge + foliado)
# ═══════════════════════════════════════════════════════════════════════════════

@app.post("/api/process")
async def process_pdfs(request: ProcessRequest):
    """
    Inicia el proceso de fusión y foliado en background.
    Al terminar (éxito o error), las carpetas de sesión se limpian automáticamente.
    """
    unknown = [fid for fid in request.file_ids if fid not in uploaded_files]
    if unknown:
        raise HTTPException(400, f"IDs no reconocidos: {len(unknown)}")
    if not request.file_ids:
        raise HTTPException(400, "Sin archivos para procesar")

    # Nombre del archivo de salida
    if request.output_name and request.output_name.strip():
        out_name = request.output_name.strip()
        if not out_name.lower().endswith(".pdf"):
            out_name += ".pdf"
    else:
        out_name = f"expediente_{datetime.now().strftime('%Y_%m_%d_%H%M')}.pdf"

    out_path = str(OUTPUT_DIR / out_name)

    # Rutas y sesiones involucradas
    file_paths  = [uploaded_files[fid].path for fid in request.file_ids]
    session_ids = list({
        uploaded_files[fid].session_id
        for fid in request.file_ids
        if uploaded_files[fid].session_id
    })

    task_id = str(uuid.uuid4())
    # Limpiar tareas finalizadas con más de 1 hora de antigüedad
    _cutoff = _time.time() - 3600
    stale = [tid for tid, t in tasks.items()
             if t["status"] in ("done", "error") and t.get("created_at", 0) < _cutoff]
    for tid in stale:
        tasks.pop(tid, None)
    if stale:
        logger.info("[proceso] %d tarea(s) antigua(s) eliminadas de memoria", len(stale))

    tasks[task_id] = {
        "id":           task_id,
        "status":       "processing",
        "progress":     0,
        "message":      "Iniciando…",
        "result_file":  None,
        "total_pages":  None,
        "failed_files": [],
        "error":        None,
        "cancelled":    False,
        "created_at":   _time.time(),
    }

    nombre = (request.nombre_expediente or request.output_name or "").strip()

    loop = asyncio.get_running_loop()
    asyncio.ensure_future(
        loop.run_in_executor(
            executor,
            _run_task,
            task_id, file_paths, out_path, out_name,
            request.config.dict(), session_ids,
            list(request.file_ids),   # IDs para limpiar del dict en memoria
            nombre,
        )
    )

    logger.info(
        "[proceso] tarea %s iniciada — %d archivo(s) → '%s' | sesiones: %s",
        task_id, len(file_paths), out_name,
        [s[:8] + "…" for s in session_ids],
    )
    return {"task_id": task_id}


def _run_task(
    task_id:           str,
    file_paths:        list,
    output_path:       str,
    output_name:       str,
    config:            dict,
    session_ids:       list,
    file_ids:          list,
    nombre_expediente: str = "",
) -> None:
    """
    Ejecuta en el hilo del ThreadPoolExecutor.
    El bloque finally garantiza la limpieza de archivos temporales
    tanto en caso de éxito como de error.
    """
    task = tasks[task_id]
    t0   = _time.time()

    def cb(msg: str, pct: float) -> None:
        if task.get("cancelled"):
            raise InterruptedError("cancelado")
        task["message"]  = msg
        task["progress"] = round(pct, 1)

    try:
        logger.info("[tarea %s] inicio del procesamiento", task_id)
        result = merge_and_foliate(file_paths, output_path, config, cb)

        # Verificar límite diario de nombre antes de registrar en el servidor
        count_antes, puede_registrar = _check_and_register_nombre(nombre_expediente)

        elapsed = round(_time.time() - t0, 1)

        if puede_registrar:
            cb("Registrando expediente…", 98)
            ok, total_mes = _registrar_expediente(output_path, nombre_expediente, result.get("total_pages", 0), elapsed)
            if not ok:
                task.update(
                    status  = "error",
                    message = "No se pudo registrar el expediente. Verifica tu conexión a internet.",
                    error   = "registro_fallido",
                )
                logger.error("[tarea %s] registro fallido — expediente no entregado", task_id)
                return
            sin_registro = False
        else:
            # Tercer uso o más del mismo nombre hoy — generar localmente sin registrar en servidor
            ok         = True
            total_mes  = None
            sin_registro = True
            logger.info(
                "[tarea %s] nombre '%s' usado %d veces hoy — expediente generado sin registrar",
                task_id, nombre_expediente, count_antes,
            )

        task.update(
            status       = "done",
            progress     = 100,
            message      = (
                f"¡Listo! {result['total_pages']} páginas"
                + (f" · expediente #{total_mes} del mes" if total_mes else "")
            ),
            result_file  = output_name,
            total_pages  = result["total_pages"],
            failed_files = result["failed_files"],
            total_mes    = total_mes,
            sin_registro = sin_registro,
            elapsed_seconds = elapsed,
        )
        logger.info(
            "[tarea %s] completada — %d págs. | %d fallo(s) | %.1fs | exp. mes: %s | sin_registro: %s",
            task_id, result["total_pages"], len(result["failed_files"]),
            elapsed, total_mes or "—", sin_registro,
        )

    except InterruptedError:
        logger.info("[tarea %s] cancelada por el usuario", task_id)
        task.update(status="cancelled", progress=0, message="Cancelado")

    except Exception as exc:
        logger.error("[tarea %s] falló: %s", task_id, exc)
        task.update(status="error", message=f"Error: {exc}", error=str(exc))

    finally:
        # ── Limpieza garantizada ───────────────────────────────────────────────
        was_cancelled = task.get("status") == "cancelled"
        if was_cancelled:
            # Sesiones preservadas: el usuario puede reintentar inmediatamente
            # con los mismos archivos sin necesidad de volver a subirlos.
            removed_from_mem = 0
            logger.info(
                "[tarea %s] cancelada — sesiones preservadas para reintento",
                task_id,
            )
        else:
            # 1. Eliminar carpetas de sesión del disco
            for sid in session_ids:
                sessions.cleanup(sid)

            # 2. Eliminar registros de memoria
            removed_from_mem = 0
            for fid in file_ids:
                if uploaded_files.pop(fid, None):
                    removed_from_mem += 1

            logger.info(
                "[tarea %s] limpieza — %d sesión(es) | %d registro(s) en memoria",
                task_id, len(session_ids), removed_from_mem,
            )


# ═══════════════════════════════════════════════════════════════════════════════
# Estado de tareas
# ═══════════════════════════════════════════════════════════════════════════════

@app.get("/api/task/{task_id}")
async def task_status(task_id: str):
    if task_id not in tasks:
        raise HTTPException(404, "Tarea no encontrada")
    return tasks[task_id]


@app.delete("/api/task/{task_id}")
async def cancel_task(task_id: str):
    if task_id not in tasks:
        raise HTTPException(404, "Tarea no encontrada")
    task = tasks[task_id]
    if task["status"] != "processing":
        return {"ok": False, "reason": "not_processing"}
    task["cancelled"] = True
    return {"ok": True}


# ═══════════════════════════════════════════════════════════════════════════════
# Descarga
# ═══════════════════════════════════════════════════════════════════════════════

@app.get("/api/download/{filename:path}")
async def download(filename: str):
    if not re.match(r'^[\w\s\-\.]+\.pdf$', filename, re.IGNORECASE):
        raise HTTPException(400, "Nombre de archivo inválido")
    path = OUTPUT_DIR / filename
    if not path.exists():
        raise HTTPException(404, "Archivo no encontrado")
    return FileResponse(str(path), media_type="application/pdf", filename=filename)


# ═══════════════════════════════════════════════════════════════════════════════
# Gestión de archivos individuales
# ═══════════════════════════════════════════════════════════════════════════════

@app.delete("/api/files/{file_id}")
async def delete_uploaded(file_id: str):
    """Elimina un archivo individual de la sesión."""
    if file_id not in uploaded_files:
        raise HTTPException(404, "Archivo no encontrado")

    info = uploaded_files.pop(file_id)
    p    = Path(info.path)
    if p.exists():
        p.unlink()

    logger.info("[archivo] eliminado: '%s' (sesión %.8s…)", info.name,
                info.session_id or "—")
    return {"status": "deleted"}


@app.post("/api/cleanup")
async def cleanup():
    """
    Limpia todos los archivos temporales en memoria y sus sesiones en disco.
    Usado por 'Limpiar todo' y 'Nuevo expediente'.
    """
    # Recopilar sesiones únicas antes de vaciar el dict
    session_ids = {
        info.session_id
        for info in uploaded_files.values()
        if info.session_id
    }
    file_count = len(uploaded_files)
    uploaded_files.clear()

    for sid in session_ids:
        sessions.cleanup(sid)

    logger.info(
        "[cleanup] %d archivo(s) y %d sesión(es) eliminadas",
        file_count, len(session_ids),
    )
    return {"files_removed": file_count, "sessions_removed": len(session_ids)}


# ═══════════════════════════════════════════════════════════════════════════════
# Auto-update
# ═══════════════════════════════════════════════════════════════════════════════

def _version_gt(v1: str, v2: str) -> bool:
    """Returns True if version string v1 is greater than v2 (semver comparison)."""
    try:
        return tuple(int(x) for x in v1.split(".")) > tuple(int(x) for x in v2.split("."))
    except Exception:
        return False


@app.get("/api/update/check")
async def update_check():
    """Informa si hay una versión nueva disponible.
    La instalación la hace el launcher al próximo inicio — la app solo notifica."""
    try:
        version_actual = _read_version_actual()
        resp = _requests.get(f"{_LICENSE_SERVER}/api/version/latest", timeout=10)
        data = resp.json()
        version_nueva = data.get("version")
        if not version_nueva:
            return {"disponible": False}
        if _version_gt(version_nueva, version_actual):
            return {
                "disponible":     True,
                "version_actual": version_actual,
                "version_nueva":  version_nueva,
                "obligatoria":    data.get("es_obligatoria", False),
                "notas":          data.get("notas", ""),
            }
        return {"disponible": False}
    except Exception as exc:
        logger.warning("[update] check falló: %s", exc)
        return {"disponible": False}


# ═══════════════════════════════════════════════════════════════════════════════
# Health
# ═══════════════════════════════════════════════════════════════════════════════

@app.get("/api/version")
async def version():
    return {"version": _read_version_actual()}


@app.get("/api/health")
async def health():
    return {
        "status":           "ok",
        "uploaded_files":   len(uploaded_files),
        "active_tasks":     sum(1 for t in tasks.values() if t["status"] == "processing"),
        "active_sessions":  len(sessions.active_sessions()),
    }


# ═══════════════════════════════════════════════════════════════════════════════
# Estado de licencia (para la UI)
# ═══════════════════════════════════════════════════════════════════════════════

# ═══════════════════════════════════════════════════════════════════════════════
# Configuración de la app (carpeta raíz de expedientes)
# ═══════════════════════════════════════════════════════════════════════════════

_META_FILE             = "expediente.json"
_INVALID_FOLDER_CHARS  = r'\/:*?"<>|'


def _config_path() -> Path:
    return _BASE / "config.json"


def _get_app_config() -> dict:
    try:
        if _config_path().exists():
            return json.loads(_config_path().read_text(encoding="utf-8"))
    except Exception:
        pass
    return {}


def _save_app_config(data: dict) -> None:
    _config_path().write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _default_expedientes_dir() -> Path:
    userprofile = os.environ.get("USERPROFILE") or os.environ.get("HOME") or ""
    if userprofile:
        d = Path(userprofile) / "Documents" / "Expedientes"
    else:
        d = _BASE / "expedientes"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _get_carpeta_raiz() -> Path:
    cr = _get_app_config().get("carpeta_raiz")
    if cr:
        p = Path(cr)
        if p.exists() and p.is_dir():
            return p
    return _default_expedientes_dir()


def _sanitize_folder_name(name: str) -> str:
    name = name.strip()
    for c in _INVALID_FOLDER_CHARS:
        name = name.replace(c, "_")
    return name[:128] or "expediente"


def _sanitize_filename(name: str) -> str:
    for c in _INVALID_FOLDER_CHARS:
        name = name.replace(c, "_")
    return name.strip(". ") or "archivo"


def _read_meta(folder: Path) -> dict:
    f = folder / _META_FILE
    if f.exists():
        try:
            return json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"nombre": folder.name, "creado": "", "orden_archivos": [], "config_folio": {}}


def _write_meta(folder: Path, meta: dict) -> None:
    (folder / _META_FILE).write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")


def _get_ordered_file_paths(folder: Path, meta: dict) -> list:
    """Returns ordered list of Path objects for PDFs in the expedition folder."""
    orden     = meta.get("orden_archivos", [])
    all_pdfs  = {f.name for f in folder.iterdir() if f.is_file() and f.suffix.lower() == ".pdf"}
    result: list = []
    seen: set    = set()
    for name in orden:
        if name in all_pdfs:
            result.append(folder / name)
            seen.add(name)
    for name in sorted(all_pdfs - seen, key=lambda s: natural_sort_key(s)):
        result.append(folder / name)
    return result


@app.get("/api/browse-folder")
async def browse_folder():
    """Abre el diálogo nativo de Windows para seleccionar carpeta."""
    try:
        import tkinter as tk
        from tkinter import filedialog
        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        path = filedialog.askdirectory(title="Seleccionar carpeta de expedientes")
        root.destroy()
        if path:
            return {"ok": True, "path": path.replace("/", "\\")}
        return {"ok": False, "path": ""}
    except Exception as e:
        return {"ok": False, "path": "", "error": str(e)}


@app.get("/api/config")
async def get_app_config():
    cfg = _get_app_config()
    carpeta = cfg.get("carpeta_raiz")
    configurada = bool(carpeta)
    if not configurada:
        carpeta = str(_default_expedientes_dir())
    return {
        "carpeta_raiz": carpeta,
        "configurada":  configurada,
    }


@app.post("/api/config")
async def save_app_config_endpoint(req: AppConfigRequest):
    p = Path(req.carpeta_raiz.strip())
    if not p.exists():
        try:
            p.mkdir(parents=True, exist_ok=True)
        except Exception as exc:
            raise HTTPException(400, f"No se pudo crear la carpeta: {exc}")
    if not p.is_dir():
        raise HTTPException(400, "La ruta no es una carpeta válida")
    cfg = _get_app_config()
    cfg["carpeta_raiz"] = str(p)
    _save_app_config(cfg)
    return {"ok": True, "carpeta_raiz": str(p)}


# ═══════════════════════════════════════════════════════════════════════════════
# Gestión de expedientes (CRUD)
# ═══════════════════════════════════════════════════════════════════════════════

@app.get("/api/expedientes")
async def list_expedientes():
    raiz = _get_carpeta_raiz()
    result = []
    try:
        for folder in sorted(raiz.iterdir(), key=lambda p: p.name.lower()):
            if not folder.is_dir() or folder.name.startswith("."):
                continue
            meta  = _read_meta(folder)
            if meta.get("archivado"):
                continue
            files = _get_ordered_file_paths(folder, meta)
            result.append({
                "nombre":   folder.name,
                "archivos": len(files),
                "creado":   meta.get("creado", ""),
            })
    except Exception as exc:
        logger.error("[expedientes] error listando: %s", exc)
    return result


@app.post("/api/expedientes", status_code=201)
async def create_expediente(req: CreateExpedienteRequest):
    nombre = _sanitize_folder_name(req.nombre)
    if not nombre:
        raise HTTPException(400, "Nombre de expediente inválido")
    raiz   = _get_carpeta_raiz()
    folder = raiz / nombre
    if folder.exists():
        raise HTTPException(409, f"Ya existe un expediente llamado '{nombre}'")
    folder.mkdir(parents=True)
    meta = {
        "nombre":          nombre,
        "creado":          datetime.now().isoformat(),
        "orden_archivos":  [],
        "config_folio": {
            "activo":           True,
            "posicion":         "top-right",
            "tamano":           11.0,
            "margen_superior":  20.0,
            "margen_lateral":   30.0,
            "iniciar_desde":    1,
        },
    }
    _write_meta(folder, meta)
    logger.info("[expediente] creado: '%s'", nombre)
    return {"nombre": nombre, "archivos": 0, "creado": meta["creado"]}


@app.put("/api/expedientes/{nombre}/rename")
async def rename_expediente(nombre: str, req: RenameExpedienteRequest):
    nuevo  = _sanitize_folder_name(req.nombre_nuevo)
    if not nuevo:
        raise HTTPException(400, "Nombre inválido")
    raiz   = _get_carpeta_raiz()
    folder = raiz / nombre
    if not folder.exists():
        raise HTTPException(404, "Expediente no encontrado")
    dest = raiz / nuevo
    if dest.exists():
        raise HTTPException(409, f"Ya existe un expediente llamado '{nuevo}'")
    folder.rename(dest)
    meta = _read_meta(dest)
    meta["nombre"] = nuevo
    _write_meta(dest, meta)
    logger.info("[expediente] renombrado: '%s' → '%s'", nombre, nuevo)
    return {"nombre": nuevo}


@app.delete("/api/expedientes/{nombre}")
async def delete_expediente(nombre: str):
    raiz   = _get_carpeta_raiz()
    folder = raiz / nombre
    if not folder.exists():
        raise HTTPException(404, "Expediente no encontrado")
    # Archive — never delete files from disk; user can access via Windows Explorer.
    meta = _read_meta(folder)
    meta["archivado"] = True
    _write_meta(folder, meta)
    logger.info("[expediente] archivado (oculto): '%s'", nombre)
    return {"ok": True}


# ═══════════════════════════════════════════════════════════════════════════════
# Archivos dentro de un expediente
# ═══════════════════════════════════════════════════════════════════════════════

@app.get("/api/expedientes/{nombre}/archivos")
async def list_archivos_expediente(nombre: str):
    raiz   = _get_carpeta_raiz()
    folder = raiz / nombre
    if not folder.exists():
        raise HTTPException(404, "Expediente no encontrado")
    meta        = _read_meta(folder)
    file_paths  = _get_ordered_file_paths(folder, meta)
    archivos    = []
    total_pages = 0
    for fp in file_paths:
        pages, err = analyze_pdf_file(str(fp))
        total_pages += max(0, pages)
        archivos.append({
            "nombre":   fp.name,
            "paginas":  pages,
            "tamanio":  fp.stat().st_size,
            "error":    err,
        })
    return {
        "archivos":     archivos,
        "total_paginas": total_pages,
        "config_folio": meta.get("config_folio", {}),
    }


@app.post("/api/expedientes/{nombre}/archivos")
async def add_archivo_expediente(
    nombre:  str,
    file:    UploadFile = File(...),
    replace: bool = Query(False),
):
    raiz   = _get_carpeta_raiz()
    folder = raiz / nombre
    if not folder.exists():
        raise HTTPException(404, "Expediente no encontrado")

    ext = Path(file.filename).suffix.lower()
    if ext not in _ALL_EXT:
        raise HTTPException(400, f"Tipo de archivo no compatible: {file.filename}")

    safe_name = _sanitize_filename(file.filename)
    dest_name = Path(safe_name).stem + ".pdf" if ext not in {".pdf"} else safe_name
    dest_path = folder / dest_name

    if dest_path.exists() and not replace:
        raise HTTPException(409, f"Ya existe '{dest_name}' en el expediente")

    temp_session = sessions.create()
    file_id      = str(uuid.uuid4())
    orig_path    = sessions.file_path(temp_session, f"{file_id}{ext}")
    pdf_path     = sessions.file_path(temp_session, f"{file_id}.pdf")

    try:
        async with aiofiles.open(str(orig_path), "wb") as fh:
            while chunk := await file.read(1024 * 1024):
                await fh.write(chunk)

        if ext in _IMAGE_EXT:
            try:
                convert_image_to_pdf(str(orig_path), str(pdf_path))
            finally:
                if orig_path.exists():
                    orig_path.unlink()
        elif ext in _WORD_EXT:
            ok = convert_docx_to_pdf(str(orig_path), str(pdf_path))
            if orig_path.exists():
                orig_path.unlink()
            if not ok:
                raise HTTPException(400, "No se pudo convertir el archivo Word a PDF")
        else:
            pdf_path = orig_path

        pages, err_msg = analyze_pdf_file(str(pdf_path))
        if pages <= 0:
            raise HTTPException(400, err_msg or "El archivo no tiene páginas válidas")

        shutil.copy2(str(pdf_path), str(dest_path))

        meta  = _read_meta(folder)
        orden = meta.get("orden_archivos", [])
        if dest_name not in orden:
            orden.append(dest_name)
        meta["orden_archivos"] = orden
        _write_meta(folder, meta)

        logger.info("[expediente] archivo agregado: '%s' → '%s' (%d págs.)", file.filename, nombre, pages)
        return {"nombre": dest_name, "paginas": pages, "tamanio": dest_path.stat().st_size}

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("[expediente] error agregando '%s': %s", file.filename, exc)
        raise HTTPException(500, str(exc))
    finally:
        sessions.cleanup(temp_session)


@app.delete("/api/expedientes/{nombre}/archivos/{filename:path}")
async def delete_archivo_expediente(nombre: str, filename: str):
    raiz   = _get_carpeta_raiz()
    folder = raiz / nombre
    if not folder.exists():
        raise HTTPException(404, "Expediente no encontrado")
    file_path = folder / filename
    if not file_path.exists():
        raise HTTPException(404, "Archivo no encontrado")
    file_path.unlink()
    meta  = _read_meta(folder)
    orden = meta.get("orden_archivos", [])
    if filename in orden:
        orden.remove(filename)
    meta["orden_archivos"] = orden
    _write_meta(folder, meta)
    logger.info("[expediente] archivo eliminado: '%s' de '%s'", filename, nombre)
    return {"ok": True}


@app.put("/api/expedientes/{nombre}/orden")
async def update_orden_expediente(nombre: str, req: UpdateOrdenRequest):
    raiz   = _get_carpeta_raiz()
    folder = raiz / nombre
    if not folder.exists():
        raise HTTPException(404, "Expediente no encontrado")
    all_pdfs = {f.name for f in folder.iterdir() if f.is_file() and f.suffix.lower() == ".pdf"}
    meta = _read_meta(folder)
    meta["orden_archivos"] = [f for f in req.orden if f in all_pdfs]
    _write_meta(folder, meta)
    return {"ok": True, "orden": meta["orden_archivos"]}


@app.put("/api/expedientes/{nombre}/config")
async def update_config_expediente(nombre: str, req: UpdateConfigFolioRequest):
    raiz   = _get_carpeta_raiz()
    folder = raiz / nombre
    if not folder.exists():
        raise HTTPException(404, "Expediente no encontrado")
    meta = _read_meta(folder)
    meta["config_folio"] = req.config_folio.model_dump()
    _write_meta(folder, meta)
    return {"ok": True}


@app.post("/api/expedientes/{nombre}/generar")
async def generar_expediente_endpoint(nombre: str, req: GenerarExpedienteRequest):
    raiz   = _get_carpeta_raiz()
    folder = raiz / nombre
    if not folder.exists():
        raise HTTPException(404, "Expediente no encontrado")

    meta       = _read_meta(folder)
    file_paths = [str(p) for p in _get_ordered_file_paths(folder, meta)]
    if not file_paths:
        raise HTTPException(400, "El expediente no tiene archivos para generar")

    if req.config_folio:
        folio_cfg = req.config_folio.model_dump()
        meta["config_folio"] = folio_cfg
        _write_meta(folder, meta)
    else:
        folio_cfg = meta.get("config_folio", {})

    gen_config = {
        "foliar":       folio_cfg.get("activo",          True),
        "font_size":    folio_cfg.get("tamano",           11.0),
        "margin_top":   folio_cfg.get("margen_superior",  20.0),
        "margin_right": folio_cfg.get("margen_lateral",   30.0),
        "position":     folio_cfg.get("posicion",         "top-right"),
        "folio_start":  folio_cfg.get("iniciar_desde",    1),
    }

    out_name = req.output_name.strip()
    if not out_name.lower().endswith(".pdf"):
        out_name += ".pdf"
    out_path = str(OUTPUT_DIR / out_name)

    task_id = str(uuid.uuid4())
    _cutoff = _time.time() - 3600
    stale   = [tid for tid, t in tasks.items()
               if t["status"] in ("done", "error") and t.get("created_at", 0) < _cutoff]
    for tid in stale:
        tasks.pop(tid, None)

    tasks[task_id] = {
        "id":           task_id,
        "status":       "processing",
        "progress":     0,
        "message":      "Iniciando…",
        "result_file":  None,
        "total_pages":  None,
        "failed_files": [],
        "error":        None,
        "cancelled":    False,
        "created_at":   _time.time(),
    }

    loop = asyncio.get_running_loop()
    asyncio.ensure_future(
        loop.run_in_executor(
            executor,
            _run_task,
            task_id, file_paths, out_path, out_name,
            gen_config,
            [],       # no temp sessions to clean
            [],       # no uploaded_files records to clean
            nombre,   # nombre_expediente for license registration
        )
    )

    logger.info("[generar] tarea %s para expediente '%s' — %d archivos", task_id, nombre, len(file_paths))
    return {"task_id": task_id}


@app.get("/api/licencia")
async def licencia_status():
    hardware_id = _get_hardware_id()
    try:
        resp = _requests.post(
            f"{_LICENSE_SERVER}/api/verificar",
            json={"hardware_id": hardware_id},
            timeout=6,
        )
        data = resp.json()
        return {
            "hardware_id":        hardware_id,
            "activa":             data.get("activa", False),
            "es_prueba":          data.get("es_prueba", False),
            "mensaje":            data.get("mensaje", ""),
            "modelo_cobro":       data.get("modelo_cobro", "por_pagina"),
            "precio_pagina":      data.get("precio_pagina", 0),
            "minimo_operacion":   data.get("minimo_operacion", 0),
            "precio_expediente":  data.get("precio_expediente", 0),
            "precio_licencia_mes":data.get("precio_licencia_mes", 0),
            "precio_licencia_ano":data.get("precio_licencia_ano", 0),
        }
    except Exception as e:
        return {
            "hardware_id": hardware_id,
            "activa":      False,
            "es_prueba":   False,
            "mensaje":     "Sin conexión al servidor de licencias.",
        }
