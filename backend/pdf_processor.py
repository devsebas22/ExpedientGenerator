import re
import logging
import os
from pathlib import Path
from typing import Callable

import fitz  # PyMuPDF

logger = logging.getLogger(__name__)


def natural_sort_key(s: str) -> list:
    """Natural sort: 1, 2, 10 in place of 1, 10, 2."""
    parts = re.split(r"(\d+)", s.lower())
    return [int(p) if p.isdigit() else p for p in parts]


def get_page_count(file_path: str) -> int:
    count, _ = analyze_pdf_file(file_path)
    return count


def analyze_pdf_file(file_path: str) -> tuple[int, str | None]:
    """Returns (page_count, error_msg). page_count is -1 if the file can't be used."""
    try:
        size = os.path.getsize(file_path)
        if size == 0:
            return -1, "Este archivo está vacío y no puede incluirse."
        doc = fitz.open(file_path)
        if doc.is_encrypted:
            if not doc.authenticate(""):
                doc.close()
                return -1, "Este archivo está protegido con contraseña. Desbloquéalo antes de subirlo."
        count = len(doc)
        doc.close()
        if count == 0:
            return -1, "Este archivo no tiene páginas legibles."
        return count, None
    except Exception as exc:
        err_str = str(exc).lower()
        if "password" in err_str or "encrypt" in err_str:
            return -1, "Este archivo está protegido con contraseña. Desbloquéalo antes de subirlo."
        logger.error("Error leyendo %s: %s", file_path, exc)
        return -1, "Este archivo está dañado y no puede leerse."


def convert_image_to_pdf(src_path: str, dst_path: str) -> None:
    """
    Convert a JPEG/PNG/etc. image to a single-page A4 PDF.

    Scaling is pixel-based: DPI metadata is ignored entirely.
    Every image is fitted within a 515×762 pt content area (A4 with ~40 pt margins)
    and centered on a 595×842 pt page, so page size is always consistent.
    """
    import io
    from PIL import Image

    with Image.open(src_path) as img:
        if img.mode not in ("RGB", "L"):
            img = img.convert("RGB")
        img_w, img_h = img.size          # pixel dimensions — ignore DPI
        buf = io.BytesIO()
        img.save(buf, format="PNG")      # lossless round-trip for fitz
        img_bytes = buf.getvalue()

    # Fit within 515×762 pt content area (A4 minus ~40 pt margins each side)
    ratio = min(515 / img_w, 762 / img_h)
    new_w = img_w * ratio
    new_h = img_h * ratio

    # Create A4 page (595×842 pt) and center the scaled image
    doc  = fitz.open()
    page = doc.new_page(width=595, height=842)
    x0   = (595 - new_w) / 2
    y0   = (842 - new_h) / 2
    page.insert_image(fitz.Rect(x0, y0, x0 + new_w, y0 + new_h), stream=img_bytes)
    doc.save(dst_path, garbage=3, deflate=True)
    doc.close()
    logger.info("Imagen convertida: '%s' → %dx%d px → %.0f×%.0f pt en A4",
                os.path.basename(src_path), img_w, img_h, new_w, new_h)


def convert_docx_to_pdf(src_path: str, dst_path: str) -> bool:
    """
    Convert .docx to PDF using python-docx + reportlab (pure Python, no LibreOffice).
    Returns True on success, False if conversion fails.
    """
    try:
        from docx import Document
        from reportlab.lib.pagesizes import letter
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.lib.units import inch

        doc = Document(src_path)
        pdf = SimpleDocTemplate(
            str(dst_path), pagesize=letter,
            leftMargin=inch, rightMargin=inch,
            topMargin=inch, bottomMargin=inch,
        )
        styles = getSampleStyleSheet()
        story = []
        for para in doc.paragraphs:
            txt = para.text.strip()
            if txt:
                story.append(Paragraph(txt, styles["Normal"]))
                story.append(Spacer(1, 4))
        if not story:
            story.append(Paragraph("(Documento sin contenido de texto visible)", styles["Normal"]))
        pdf.build(story)
        logger.info("DOCX convertido: '%s'", os.path.basename(dst_path))
        return True
    except Exception as exc:
        logger.warning("Conversión DOCX falló: %s", exc)
        return False


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

    # ── Phase 2: foliate (optional) ───────────────────────────────────────────
    if config.get("foliar", True):
        font_size    = float(config.get("font_size",    11))
        margin_top   = float(config.get("margin_top",   20))
        margin_right = float(config.get("margin_right", 30))
        position     = config.get("position", "top-right")

        for page_num in range(total_pages):
            if page_num % 25 == 0 or page_num == total_pages - 1:
                pct = 48 + ((page_num + 1) / total_pages) * 46
                progress_cb(f"Foliando página {page_num + 1} de {total_pages}", pct)
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
    else:
        progress_cb("Sin foliación — omitiendo numeración…", 94)

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
