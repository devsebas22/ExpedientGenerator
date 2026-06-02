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


# Oficio colombiano: 216 × 330 mm = 612 × 935 pt
_OFICIO_W = 612.0
_OFICIO_H = 935.0


def convert_image_to_pdf(src_path: str, dst_path: str) -> None:
    """
    Convierte imagen a PDF de una página en tamaño Oficio (612×935 pt).
    Escalado por píxeles; DPI ignorado. Imagen centrada con ~40 pt de margen.
    """
    import io
    from PIL import Image

    with Image.open(src_path) as img:
        if img.mode not in ("RGB", "L"):
            img = img.convert("RGB")
        img_w, img_h = img.size
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        img_bytes = buf.getvalue()

    content_w = _OFICIO_W - 80
    content_h = _OFICIO_H - 80
    ratio = min(content_w / img_w, content_h / img_h)
    new_w, new_h = img_w * ratio, img_h * ratio

    doc  = fitz.open()
    page = doc.new_page(width=_OFICIO_W, height=_OFICIO_H)
    x0   = (_OFICIO_W - new_w) / 2
    y0   = (_OFICIO_H - new_h) / 2
    page.insert_image(fitz.Rect(x0, y0, x0 + new_w, y0 + new_h), stream=img_bytes)
    doc.save(dst_path, garbage=3, deflate=True)
    doc.close()
    logger.info("Imagen → Oficio: '%s' %dx%d px → %.0f×%.0f pt",
                os.path.basename(src_path), img_w, img_h, new_w, new_h)


def convert_docx_to_pdf(src_path: str, dst_path: str) -> bool:
    """
    Convert .docx to PDF using python-docx + reportlab (pure Python, no LibreOffice).
    Returns True on success, False if conversion fails.
    """
    try:
        from docx import Document
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.lib.units import inch

        _oficio_rl = (_OFICIO_W, _OFICIO_H)   # reportlab usa (ancho, alto) en pt
        doc = Document(src_path)
        pdf = SimpleDocTemplate(
            str(dst_path), pagesize=_oficio_rl,
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


def _normalize_page_in_place(doc: fitz.Document, page_idx: int) -> None:
    """
    Escala y centra una página no-Oficio a tamaño Oficio modificando su
    content stream directamente. Sin show_pdf_page → sin Form XObjects →
    los recursos ya se importaron una sola vez al llamar insert_pdf(src).

    Coordenadas PDF: origen en esquina inferior-izquierda, Y crece hacia arriba.
    El CTM  q scale 0 0 scale tx ty cm  transforma (x,y) → (x·s+tx, y·s+ty).
    """
    page = doc[page_idx]
    if page.rotation != 0:
        # Páginas rotadas son muy raras — omitir normalización es aceptable
        logger.warning("Página %d tiene rotación %d — omitiendo normalización Oficio",
                       page_idx, page.rotation)
        return

    w, h = page.rect.width, page.rect.height
    scale = min(_OFICIO_W / w, _OFICIO_H / h)
    nw, nh = w * scale, h * scale
    tx = (_OFICIO_W - nw) / 2
    ty = (_OFICIO_H - nh) / 2   # margen inferior en coordenadas PDF (y hacia arriba)

    try:
        page.clean_contents()
        xrefs = page.get_contents()
        if xrefs:
            xref = xrefs[0]
            old = doc.xref_stream(xref)
            ctm = f"q {scale:.6f} 0 0 {scale:.6f} {tx:.4f} {ty:.4f} cm\n".encode()
            doc.update_stream(xref, ctm + old + b"\nQ")
        page.set_mediabox(fitz.Rect(0, 0, _OFICIO_W, _OFICIO_H))
    except Exception as exc:
        logger.warning("No se pudo normalizar página %d in-place: %s", page_idx, exc)


def _insert_normalized(output_doc: fitz.Document, src: fitz.Document) -> None:
    """
    Inserta todas las páginas de src en output_doc normalizadas a Oficio.

    Rendimiento: insert_pdf una sola vez importa los recursos del documento
    fuente exactamente una vez. Las páginas no-Oficio se normalizan in-place
    modificando su content stream (sin show_pdf_page, sin Form XObjects).

    show_pdf_page duplicaba recursos por cada llamada; con garbage=3 al
    guardar eso causaba O(n²) en documentos con muchas páginas no-Oficio.
    """
    n = len(src)

    def _is_oficio(pno: int) -> bool:
        r = src[pno].rect
        return abs(r.width - _OFICIO_W) <= 2 and abs(r.height - _OFICIO_H) <= 2

    start = len(output_doc)
    output_doc.insert_pdf(src)   # recursos importados una sola vez

    for pno in range(n):
        if not _is_oficio(pno):
            _normalize_page_in_place(output_doc, start + pno)


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
            _insert_normalized(output_doc, src)
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
        folio_start  = max(1, int(config.get("folio_start", 1)))

        for page_num in range(total_pages):
            if page_num % 25 == 0 or page_num == total_pages - 1:
                pct = 48 + ((page_num + 1) / total_pages) * 46
                progress_cb(f"Foliando página {folio_start + page_num} de {folio_start + total_pages - 1}", pct)
            try:
                _stamp_folio(
                    output_doc[page_num],
                    folio_start + page_num,
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
            garbage=2,     # compact XREF (3 = también comprime streams, lento con muchos XObjects)
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
