import re
import logging
import os
from typing import Callable

import fitz  # PyMuPDF

logger = logging.getLogger(__name__)


def natural_sort_key(s: str) -> list:
    """Natural sort: 1, 2, 10 in place of 1, 10, 2."""
    parts = re.split(r"(\d+)", s.lower())
    return [int(p) if p.isdigit() else p for p in parts]


def get_page_count(file_path: str) -> int:
    try:
        doc = fitz.open(file_path)
        count = len(doc)
        doc.close()
        return count
    except Exception as exc:
        logger.error("Error leyendo %s: %s", file_path, exc)
        return -1


def merge_and_foliate(
    file_paths: list[str],
    output_path: str,
    config: dict,
    progress_cb: Callable[[str, float], None],
) -> dict:
    """
    Merge ordered PDFs and stamp a folio number on every page.
    Returns {'total_pages': int, 'failed_files': list[str]}.
    Raises ValueError if no file could be processed.
    """
    failed_files: list[str] = []
    output_doc = fitz.open()

    total = len(file_paths)

    # ── Phase 1: merge ────────────────────────────────────────────────────────
    for i, fpath in enumerate(file_paths):
        fname = os.path.basename(fpath)
        progress_cb(f"Fusionando ({i + 1}/{total}): {fname}", (i / total) * 48)

        try:
            src = fitz.open(fpath)
            if src.is_encrypted:
                if not src.authenticate(""):
                    failed_files.append(f"{fname} (encriptado, sin contraseña)")
                    src.close()
                    continue
            output_doc.insert_pdf(src)
            page_count = len(src)
            src.close()
            logger.info("Fusionado '%s'  %d págs.", fname, page_count)
        except Exception as exc:
            logger.error("Error en '%s': %s", fname, exc)
            failed_files.append(f"{fname} ({str(exc)[:80]})")

    if len(output_doc) == 0:
        output_doc.close()
        raise ValueError(
            "No se pudo procesar ningún archivo. "
            f"Fallaron: {', '.join(failed_files)}"
        )

    total_pages = len(output_doc)

    # ── Phase 2: foliate ──────────────────────────────────────────────────────
    font_size   = float(config.get("font_size",   11))
    margin_top  = float(config.get("margin_top",  20))
    margin_right = float(config.get("margin_right", 30))
    position    = config.get("position", "top-right")

    for page_num in range(total_pages):
        if page_num % 25 == 0 or page_num == total_pages - 1:
            pct = 48 + ((page_num + 1) / total_pages) * 46
            progress_cb(
                f"Foliando página {page_num + 1} de {total_pages}", pct
            )
        try:
            _stamp_folio(
                output_doc[page_num],
                page_num + 1,
                font_size,
                margin_top,
                margin_right,
                position,
            )
        except Exception as exc:
            logger.warning("No se pudo foliar página %d: %s", page_num + 1, exc)

    # ── Phase 3: save ─────────────────────────────────────────────────────────
    progress_cb("Guardando expediente…", 95)
    try:
        output_doc.save(
            output_path,
            garbage=3,     # remove unreferenced objects
            deflate=True,  # compress streams
            clean=False,   # do NOT re-parse content streams → preserves quality
        )
    finally:
        output_doc.close()

    progress_cb("¡Expediente generado con éxito!", 100)
    logger.info("Guardado en '%s'  %d págs.  %d fallos.", output_path, total_pages, len(failed_files))

    return {"total_pages": total_pages, "failed_files": failed_files}


def _stamp_folio(
    page: fitz.Page,
    number: int,
    font_size: float,
    margin_top: float,
    margin_right: float,
    position: str,
) -> None:
    """Insert folio number text on a page."""
    rect = page.rect
    text = str(number)
    box_w = max(70.0, len(text) * font_size * 0.85)
    box_h = font_size + 6.0

    if position == "top-right":
        x1 = rect.width  - margin_right
        x0 = x1 - box_w
        y0 = margin_top
        y1 = margin_top + box_h
        align = 2  # right
    elif position == "top-left":
        x0 = margin_right
        x1 = x0 + box_w
        y0 = margin_top
        y1 = margin_top + box_h
        align = 0  # left
    elif position == "bottom-right":
        x1 = rect.width - margin_right
        x0 = x1 - box_w
        y1 = rect.height - margin_top
        y0 = y1 - box_h
        align = 2
    else:  # bottom-left
        x0 = margin_right
        x1 = x0 + box_w
        y1 = rect.height - margin_top
        y0 = y1 - box_h
        align = 0

    rc = page.insert_textbox(
        fitz.Rect(x0, y0, x1, y1),
        text,
        fontsize=font_size,
        fontname="helv",
        color=(0, 0, 0),
        align=align,
    )
    if rc < 0:
        # Fallback: insert_text with manual positioning
        x = x1 - 4 if align == 2 else x0
        page.insert_text(
            (x, y0 + font_size),
            text,
            fontsize=font_size,
            fontname="helv",
            color=(0, 0, 0),
        )
