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
import logging
import re
import shutil
import uuid
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import aiofiles
from fastapi import FastAPI, File, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from .models import CountRequest, FileInfo, FolderRequest, FolioConfig, ProcessRequest
from .pdf_processor import get_page_count, merge_and_foliate, natural_sort_key
from .session_manager import SessionManager

# ── Rutas base ─────────────────────────────────────────────────────────────────
TEMP_DIR   = Path("temp")
OUTPUT_DIR = Path("expedientes_generados")
LOG_DIR    = Path("logs")

for _d in (TEMP_DIR, OUTPUT_DIR, LOG_DIR):
    _d.mkdir(exist_ok=True)

# ── Logging ────────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR / "expediente.log", encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
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
app = FastAPI(title="Expediente Digital", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

FRONTEND = Path(__file__).parent.parent / "frontend"
if FRONTEND.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND)), name="static")


@app.get("/")
async def root():
    return FileResponse(str(FRONTEND / "index.html"))


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

@app.post("/api/upload")
async def upload_file(
    file: UploadFile = File(...),
    session_id: Optional[str] = Query(None, description="ID de sesión temporal"),
):
    """
    Recibe un PDF y lo guarda en temp/session_<id>/<uuid>.pdf.
    Si no se provee session_id (o es inválido/expirado), crea una nueva sesión.
    """
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(400, f"Solo se aceptan PDFs: {file.filename}")

    # Crear sesión si no viene o está vencida
    if not session_id or not sessions.exists(session_id):
        session_id = sessions.create()
        logger.debug("[upload] sesión creada automáticamente: %s", session_id)

    file_id   = str(uuid.uuid4())
    file_path = sessions.file_path(session_id, f"{file_id}.pdf")

    try:
        async with aiofiles.open(str(file_path), "wb") as fh:
            while chunk := await file.read(1024 * 1024):   # 1 MB chunks
                await fh.write(chunk)

        pages = get_page_count(str(file_path))

        info = FileInfo(
            id         = file_id,
            name       = file.filename,
            size       = file_path.stat().st_size,
            pages      = pages,
            path       = str(file_path),
            session_id = session_id,
            error      = "No se pudo leer el PDF" if pages == -1 else None,
        )
        uploaded_files[file_id] = info
        logger.info(
            "[upload] '%s' → sesión %.8s… | %d págs. | %.1f MB",
            file.filename, session_id, pages, info.size / 1_048_576,
        )
        return info

    except Exception as exc:
        if file_path.exists():
            file_path.unlink()
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
    tasks[task_id] = {
        "id":           task_id,
        "status":       "processing",
        "progress":     0,
        "message":      "Iniciando…",
        "result_file":  None,
        "total_pages":  None,
        "failed_files": [],
        "error":        None,
    }

    loop = asyncio.get_running_loop()
    asyncio.ensure_future(
        loop.run_in_executor(
            executor,
            _run_task,
            task_id, file_paths, out_path, out_name,
            request.config.dict(), session_ids,
            list(request.file_ids),   # IDs para limpiar del dict en memoria
        )
    )

    logger.info(
        "[proceso] tarea %s iniciada — %d archivo(s) → '%s' | sesiones: %s",
        task_id, len(file_paths), out_name,
        [s[:8] + "…" for s in session_ids],
    )
    return {"task_id": task_id}


def _run_task(
    task_id:     str,
    file_paths:  list,
    output_path: str,
    output_name: str,
    config:      dict,
    session_ids: list,
    file_ids:    list,
) -> None:
    """
    Ejecuta en el hilo del ThreadPoolExecutor.
    El bloque finally garantiza la limpieza de archivos temporales
    tanto en caso de éxito como de error.
    """
    task = tasks[task_id]

    def cb(msg: str, pct: float) -> None:
        task["message"]  = msg
        task["progress"] = round(pct, 1)

    try:
        logger.info("[tarea %s] inicio del procesamiento", task_id)
        result = merge_and_foliate(file_paths, output_path, config, cb)

        task.update(
            status       = "done",
            progress     = 100,
            message      = f"¡Listo! {result['total_pages']} páginas",
            result_file  = output_name,
            total_pages  = result["total_pages"],
            failed_files = result["failed_files"],
        )
        logger.info(
            "[tarea %s] completada — %d págs. | %d fallo(s)",
            task_id, result["total_pages"], len(result["failed_files"]),
        )

    except Exception as exc:
        logger.error("[tarea %s] falló: %s", task_id, exc)
        task.update(status="error", message=f"Error: {exc}", error=str(exc))

    finally:
        # ── Limpieza garantizada ───────────────────────────────────────────────
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
# Health
# ═══════════════════════════════════════════════════════════════════════════════

@app.get("/api/health")
async def health():
    return {
        "status":           "ok",
        "uploaded_files":   len(uploaded_files),
        "active_tasks":     sum(1 for t in tasks.values() if t["status"] == "processing"),
        "active_sessions":  len(sessions.active_sessions()),
    }
