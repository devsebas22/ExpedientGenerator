import asyncio
import logging
import re
import shutil
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
from typing import Dict

import aiofiles
import fitz
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .models import FileInfo, FolderRequest, FolioConfig, ProcessRequest
from .pdf_processor import get_page_count, merge_and_foliate, natural_sort_key

# ── Logging ───────────────────────────────────────────────────────────────────
LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR / "expediente.log", encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)

# ── Paths ─────────────────────────────────────────────────────────────────────
TEMP_DIR   = Path("temp")
OUTPUT_DIR = Path("expedientes_generados")
TEMP_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)

# ── In-memory state ───────────────────────────────────────────────────────────
# {file_id: FileInfo}
uploaded_files: Dict[str, FileInfo] = {}

# {task_id: dict}  — plain dict so background thread can mutate freely
tasks: Dict[str, dict] = {}

executor = ThreadPoolExecutor(max_workers=2)

# ── FastAPI ───────────────────────────────────────────────────────────────────
app = FastAPI(title="Expediente Digital", version="1.0.0")

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


# ── Upload ────────────────────────────────────────────────────────────────────

@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...)):
    """Receive one PDF and store it in the temp folder."""
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(400, f"Solo se aceptan PDFs: {file.filename}")

    file_id  = str(uuid.uuid4())
    tmp_path = TEMP_DIR / f"{file_id}.pdf"

    try:
        async with aiofiles.open(str(tmp_path), "wb") as f:
            while chunk := await file.read(1024 * 1024):  # 1 MB chunks
                await f.write(chunk)

        pages = get_page_count(str(tmp_path))

        info = FileInfo(
            id=file_id,
            name=file.filename,
            size=tmp_path.stat().st_size,
            pages=pages,
            path=str(tmp_path),
            error="No se pudo leer el PDF" if pages == -1 else None,
        )
        uploaded_files[file_id] = info
        logger.info("Subido '%s' → %d págs.", file.filename, pages)
        return info

    except Exception as exc:
        if tmp_path.exists():
            tmp_path.unlink()
        logger.error("Error subiendo '%s': %s", file.filename, exc)
        raise HTTPException(500, str(exc))


# ── Load from local folder ────────────────────────────────────────────────────

@app.post("/api/load-folder")
async def load_folder(request: FolderRequest):
    """Copy every PDF found in a local folder into temp and return file info."""
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

    results = []
    for pdf in pdfs:
        file_id  = str(uuid.uuid4())
        tmp_path = TEMP_DIR / f"{file_id}.pdf"
        try:
            shutil.copy2(str(pdf), str(tmp_path))
            pages = get_page_count(str(tmp_path))
            info  = FileInfo(
                id=file_id,
                name=pdf.name,
                size=tmp_path.stat().st_size,
                pages=pages,
                path=str(tmp_path),
            )
            uploaded_files[file_id] = info
            results.append(info)
        except Exception as exc:
            logger.error("Error cargando '%s': %s", pdf.name, exc)
            results.append(
                FileInfo(id=str(uuid.uuid4()), name=pdf.name,
                         size=0, pages=-1, path="", error=str(exc))
            )

    return results


# ── Process ───────────────────────────────────────────────────────────────────

@app.post("/api/process")
async def process_pdfs(request: ProcessRequest):
    """Start background merge + foliate task."""
    unknown = [fid for fid in request.file_ids if fid not in uploaded_files]
    if unknown:
        raise HTTPException(400, f"IDs no reconocidos: {len(unknown)}")
    if not request.file_ids:
        raise HTTPException(400, "Sin archivos para procesar")

    # Build output filename
    if request.output_name and request.output_name.strip():
        out_name = request.output_name.strip()
        if not out_name.lower().endswith(".pdf"):
            out_name += ".pdf"
    else:
        out_name = f"expediente_{datetime.now().strftime('%Y_%m_%d_%H%M')}.pdf"

    out_path  = str(OUTPUT_DIR / out_name)
    task_id   = str(uuid.uuid4())
    file_paths = [uploaded_files[fid].path for fid in request.file_ids]

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
            request.config.dict(),
        )
    )

    logger.info("Tarea %s iniciada (%d archivos → %s)", task_id, len(file_paths), out_name)
    return {"task_id": task_id}


def _run_task(
    task_id: str,
    file_paths: list,
    output_path: str,
    output_name: str,
    config: dict,
) -> None:
    task = tasks[task_id]

    def cb(msg: str, pct: float) -> None:
        task["message"]  = msg
        task["progress"] = round(pct, 1)

    try:
        result = merge_and_foliate(file_paths, output_path, config, cb)
        task.update(
            status="done",
            progress=100,
            message=f"¡Listo! {result['total_pages']} páginas",
            result_file=output_name,
            total_pages=result["total_pages"],
            failed_files=result["failed_files"],
        )
    except Exception as exc:
        logger.error("Tarea %s falló: %s", task_id, exc)
        task.update(status="error", message=f"Error: {exc}", error=str(exc))


# ── Task status ───────────────────────────────────────────────────────────────

@app.get("/api/task/{task_id}")
async def task_status(task_id: str):
    if task_id not in tasks:
        raise HTTPException(404, "Tarea no encontrada")
    return tasks[task_id]


# ── Download ──────────────────────────────────────────────────────────────────

@app.get("/api/download/{filename:path}")
async def download(filename: str):
    # Prevent path traversal
    if not re.match(r'^[\w\s\-\.]+\.pdf$', filename, re.IGNORECASE):
        raise HTTPException(400, "Nombre de archivo inválido")
    path = OUTPUT_DIR / filename
    if not path.exists():
        raise HTTPException(404, "Archivo no encontrado")
    return FileResponse(str(path), media_type="application/pdf", filename=filename)


# ── File management ───────────────────────────────────────────────────────────

@app.delete("/api/files/{file_id}")
async def delete_uploaded(file_id: str):
    if file_id not in uploaded_files:
        raise HTTPException(404, "Archivo no encontrado")
    info = uploaded_files.pop(file_id)
    p = Path(info.path)
    if p.exists():
        p.unlink()
    return {"status": "deleted"}


@app.post("/api/cleanup")
async def cleanup():
    """Remove all uploaded temp files from this session."""
    removed = 0
    for fid, info in list(uploaded_files.items()):
        p = Path(info.path)
        if p.exists():
            p.unlink()
            removed += 1
        del uploaded_files[fid]
    return {"removed": removed}


@app.get("/api/health")
async def health():
    return {
        "status": "ok",
        "uploaded": len(uploaded_files),
        "tasks":    len(tasks),
    }
