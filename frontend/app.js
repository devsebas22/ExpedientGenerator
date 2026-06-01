"use strict";
/* ═══════════════════════════════════════════════════════════════════════════
   Expediente Digital – frontend logic
   ═════════════════════════════════════════════════════════════════════════ */

const API = "";          // same origin
const POLL_MS = 700;     // progress poll interval

/* ── SVG icon strings ────────────────────────────────────────────────────── */
var ICO_FILE   = `<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>`;
var ICO_IMAGE  = `<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="18" height="18" rx="2" ry="2"/><circle cx="8.5" cy="8.5" r="1.5"/><polyline points="21 15 16 10 5 21"/></svg>`;
var ICO_WORD   = `<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/><line x1="10" y1="9" x2="8" y2="9"/></svg>`;
var ICO_GRIP   = `<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="9" cy="5" r="1"/><circle cx="9" cy="12" r="1"/><circle cx="9" cy="19" r="1"/><circle cx="15" cy="5" r="1"/><circle cx="15" cy="12" r="1"/><circle cx="15" cy="19" r="1"/></svg>`;
var ICO_ZAP    = `<svg xmlns="http://www.w3.org/2000/svg" width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg>`;
var ICO_UPLOAD = `<svg xmlns="http://www.w3.org/2000/svg" width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/></svg>`;
var ICO_REFRESH= `<svg xmlns="http://www.w3.org/2000/svg" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="23 4 23 10 17 10"/><polyline points="1 20 1 14 7 14"/><path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"/></svg>`;
var ICO_FOLDER_SM = `<svg xmlns="http://www.w3.org/2000/svg" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/></svg>`;
var ICO_CLOCK  = `<svg xmlns="http://www.w3.org/2000/svg" width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>`;
var ICO_WARN   = `<svg xmlns="http://www.w3.org/2000/svg" width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>`;
var ICO_WARN_MD= `<svg xmlns="http://www.w3.org/2000/svg" width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>`;
var ICO_CIRCLE = `<svg xmlns="http://www.w3.org/2000/svg" width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><polyline points="16 12 12 8 8 12"/><line x1="12" y1="16" x2="12" y2="8"/></svg>`;
var ICO_OK_TOAST    = `<svg xmlns="http://www.w3.org/2000/svg" width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>`;
var ICO_ERR_TOAST   = `<svg xmlns="http://www.w3.org/2000/svg" width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>`;
var ICO_WARN_TOAST  = `<svg xmlns="http://www.w3.org/2000/svg" width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>`;
var ICO_INFO_TOAST  = `<svg xmlns="http://www.w3.org/2000/svg" width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>`;

/* ── State ──────────────────────────────────────────────────────────────── */
// [{id, name, size, pages, session_id, error}]  — ordered as the user sees them
let files          = [];
let pollTimer      = null;
let currentSession = null;   // session_id activo para uploads

/* ── DOM refs ────────────────────────────────────────────────────────────── */
const dropZone       = document.getElementById("drop-zone");
const fileInput      = document.getElementById("file-input");
const folderInput    = document.getElementById("folder-input");
const folderPath     = document.getElementById("folder-path");
const fileList       = document.getElementById("file-list");
const badgeFiles     = document.getElementById("badge-files");
const badgePages     = document.getElementById("badge-pages");
const btnGenerate    = document.getElementById("btn-generate");
const actionSummary  = document.getElementById("action-summary");
const progressSec    = document.getElementById("progress-section");
const progressFill   = document.getElementById("progress-fill");
const progressMsg    = document.getElementById("progress-msg");
const progressPct    = document.getElementById("progress-pct");
const resultSec      = document.getElementById("result-section");
const resultName     = document.getElementById("result-name");
const resultMeta     = document.getElementById("result-meta");
const btnDownload    = document.getElementById("btn-download");
const failedWarn     = document.getElementById("failed-warn");
const failedList     = document.getElementById("failed-list");
// Counter panel
const counterCard    = document.getElementById("counter-card");
const counterNumEl   = document.getElementById("counter-num");
const counterChips   = document.getElementById("counter-chips");
const counterWarn    = document.getElementById("counter-warn");

/* ═══════════════════════════════════════════════════════════════════════════
   Counter helpers
   ═════════════════════════════════════════════════════════════════════════ */
function estimateTime(pages, fileCount) {
  if (pages === 0) return null;
  // ~150 pages/s for stamp pass + ~0.5 s/file for I/O overhead
  const secs = Math.max(2, Math.ceil(pages / 150) + Math.ceil(fileCount * 0.5));
  return secs < 60 ? `~${secs}s` : `~${Math.ceil(secs / 60)} min`;
}

function sizeCategory(pages) {
  if (pages === 0)   return null;
  if (pages < 100)   return { cls: "ok",  label: "Pequeño"    };
  if (pages < 500)   return { cls: "",    label: "Mediano"    };
  if (pages < 1000)  return { cls: "big", label: "Grande"     };
  if (pages < 2000)  return { cls: "big", label: "Muy grande" };
  return               { cls: "huge", label: "Masivo"      };
}

function easeOut(t) { return 1 - Math.pow(1 - t, 3); }

function animateCounter(el, from, to, ms = 400) {
  const start = performance.now();
  el.classList.add("bump");
  const step = (now) => {
    const p = Math.min((now - start) / ms, 1);
    el.textContent = Math.round(from + (to - from) * easeOut(p)).toLocaleString("es");
    if (p < 1) requestAnimationFrame(step);
    else        el.classList.remove("bump");
  };
  requestAnimationFrame(step);
}

/* ═══════════════════════════════════════════════════════════════════════════
   Gestión de sesiones temporales
   ═════════════════════════════════════════════════════════════════════════ */

/**
 * Devuelve el session_id activo, creando uno nuevo en el backend si hace falta.
 * Si el backend reportó que la sesión expiró durante un upload previo, la
 * respuesta del upload incluirá el nuevo session_id y _syncSession lo actualizará.
 */
async function ensureSession() {
  if (currentSession) return currentSession;
  const res = await fetch(`${API}/api/session`, { method: "POST" });
  if (!res.ok) throw new Error("No se pudo crear sesión temporal en el servidor");
  const { session_id } = await res.json();
  currentSession = session_id;
  return session_id;
}

/**
 * Sincroniza el session_id local con el que devuelve el backend.
 * Si el backend creó una sesión nueva (porque la anterior expiró), la adoptamos.
 */
function _syncSession(fileInfo) {
  if (fileInfo.session_id && fileInfo.session_id !== currentSession) {
    currentSession = fileInfo.session_id;
  }
}

/** Descarta la sesión local. La limpieza en disco ya ocurrió en el backend. */
function resetSession() {
  currentSession = null;
}

/* ═══════════════════════════════════════════════════════════════════════════
   Natural sort
   ═════════════════════════════════════════════════════════════════════════ */
function naturalSortKey(s) {
  return s.replace(/(\d+)/g, (n) => n.padStart(12, "0")).toLowerCase();
}
function naturalSort(arr) {
  return [...arr].sort((a, b) =>
    naturalSortKey(a.name).localeCompare(naturalSortKey(b.name))
  );
}

/* ═══════════════════════════════════════════════════════════════════════════
   UI helpers
   ═════════════════════════════════════════════════════════════════════════ */
function fmtSize(bytes) {
  if (bytes < 1024)       return bytes + " B";
  if (bytes < 1048576)    return (bytes / 1024).toFixed(1) + " KB";
  return (bytes / 1048576).toFixed(1) + " MB";
}

function toast(msg, type = "info", dur = 3500) {
  const icons = { success: ICO_OK_TOAST, error: ICO_ERR_TOAST, warn: ICO_WARN_TOAST, info: ICO_INFO_TOAST };
  const t = document.createElement("div");
  t.className = `toast ${type}`;
  t.innerHTML = `<span class="toast-icon">${icons[type] || ICO_INFO_TOAST}</span><span class="toast-msg">${msg}</span>`;
  document.getElementById("toast-container").append(t);
  setTimeout(() => t.remove(), dur);
}

function setGenerateBtn() {
  const ready = files.filter((f) => !f.uploading).length;
  btnGenerate.disabled = ready === 0;
  btnGenerate.innerHTML = ready === 0
    ? `${ICO_UPLOAD} Carga al menos un archivo para continuar`
    : `${ICO_ZAP} Generar expediente`;
}

function setProcessing(on) {
  btnGenerate.disabled = on || files.filter((f) => !f.uploading).length === 0;
  btnGenerate.innerHTML = on
    ? `<span class="spinner"></span> Procesando…`
    : files.filter((f) => !f.uploading).length === 0
      ? `${ICO_UPLOAD} Carga al menos un archivo para continuar`
      : `${ICO_ZAP} Generar expediente`;
}

/* ═══════════════════════════════════════════════════════════════════════════
   File type helpers
   ═════════════════════════════════════════════════════════════════════════ */
const _IMG_EXT  = new Set(["jpg","jpeg","png","gif","bmp","tiff","webp"]);
const _WORD_EXT = new Set(["docx","doc"]);
const _ALL_EXT  = new Set([..._IMG_EXT, ..._WORD_EXT, "pdf"]);

function fileIcon(name) {
  const ext = name.split(".").pop().toLowerCase();
  if (_IMG_EXT.has(ext))  return ICO_IMAGE;
  if (_WORD_EXT.has(ext)) return ICO_WORD;
  return ICO_FILE;
}

/* ═══════════════════════════════════════════════════════════════════════════
   Render file list
   ═════════════════════════════════════════════════════════════════════════ */
function renderList() {
  fileList.innerHTML = "";

  files.forEach((f, i) => {
    const li = document.createElement("li");
    const isUploading = !!f.uploading;
    const hasError    = !isUploading && f.pages <= 0;

    li.className  = isUploading ? "file-item uploading-item"
                  : hasError    ? "file-item error-item"
                  : "file-item";
    li.draggable  = !isUploading;
    li.dataset.id = f.id;

    const pagesHtml = isUploading
      ? `<span class="pages-loading"><span class="spinner-sm"></span> subiendo…</span>`
      : f.pages > 0
        ? `<span class="pages-badge">${f.pages} págs.</span>`
        : `<span class="err" title="${esc(f.error || '')}">⚠ ${esc(f.error || "Error leyendo")}</span>`;

    const removeBtn = isUploading
      ? `<span style="width:26px"></span>`
      : `<button class="btn-remove" title="Eliminar" data-id="${f.id}">✕</button>`;

    li.innerHTML = `
      <span class="handle" style="${isUploading ? "opacity:.15;pointer-events:none" : ""}">${ICO_GRIP}</span>
      <span class="file-num">${i + 1}</span>
      <span class="file-icon">${fileIcon(f.name)}</span>
      <div class="file-info">
        <div class="file-name" title="${esc(f.name)}">${esc(f.name)}</div>
        <div class="file-meta">${pagesHtml}${esc(fmtSize(f.size))}</div>
      </div>
      ${removeBtn}
    `;

    fileList.append(li);
  });

  initDragSort();
  updateSummary();
}

function esc(s) {
  return String(s)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function updateSummary() {
  const uploading = files.filter((f) => f.uploading);
  const ready     = files.filter((f) => !f.uploading);
  const errored   = ready.filter((f) => f.pages <= 0);
  const total     = ready.reduce((s, f) => s + (f.pages > 0 ? f.pages : 0), 0);

  // ── Small header badges ──────────────────────────────────────────────────
  badgeFiles.textContent = `${files.length} archivo${files.length !== 1 ? "s" : ""}`;
  if (uploading.length > 0) {
    badgePages.innerHTML =
      `<span class="spinner-sm"></span> ${uploading.length} subiendo…`;
  } else {
    badgePages.textContent = `${total.toLocaleString("es")} página${total !== 1 ? "s" : ""}`;
  }

  // ── Generate button ──────────────────────────────────────────────────────
  setGenerateBtn();

  // ── Action summary text ──────────────────────────────────────────────────
  if (files.length === 0) {
    actionSummary.innerHTML = "Arrastra archivos aquí o usa los botones de arriba.";
  } else if (uploading.length > 0) {
    actionSummary.innerHTML =
      `Subiendo <strong>${uploading.length}</strong> archivo(s)… espera para continuar.`;
  } else {
    const t = estimateTime(total, ready.length);
    actionSummary.innerHTML =
      `<strong>${ready.length}</strong> archivo${ready.length !== 1 ? "s" : ""} · ` +
      `<strong>${total.toLocaleString("es")}</strong> páginas en total` +
      (t ? ` · tiempo estimado: <strong>${t}</strong>` : "") +
      ` · puedes reordenar arrastrando las filas.`;
  }

  // ── Counter card ─────────────────────────────────────────────────────────
  if (files.length === 0) {
    counterCard.style.display = "none";
    return;
  }
  counterCard.style.display = "";

  // Animated number
  const prev = parseInt(counterNumEl.textContent.replace(/\D/g, "")) || 0;
  if (prev !== total) animateCounter(counterNumEl, prev, total);

  // Chips
  const time = estimateTime(total, ready.length);
  const cat  = sizeCategory(total);
  const chipsHtml = [
    `<span class="chip">${ICO_FOLDER_SM} ${ready.length} archivo${ready.length !== 1 ? "s" : ""}</span>`,
    uploading.length
      ? `<span class="chip"><span class="spinner-sm"></span> ${uploading.length} subiendo</span>`
      : "",
    time
      ? `<span class="chip time">${ICO_CLOCK} ${time}</span>`
      : "",
    errored.length
      ? `<span class="chip err">${ICO_WARN} ${errored.length} con error</span>`
      : "",
    cat
      ? `<span class="chip ${cat.cls}">${cat.label}</span>`
      : "",
  ].filter(Boolean).join("");
  counterChips.innerHTML = chipsHtml;

  // Warning strip
  if (total > 2000) {
    counterWarn.style.display = "";
    counterWarn.className = "counter-warn-strip danger";
    counterWarn.innerHTML =
      `${ICO_WARN_MD} <span>Expediente masivo: <strong>${total.toLocaleString("es")} páginas</strong>. ` +
      `El procesamiento puede tardar varios minutos.</span>`;
  } else if (total > 1000) {
    counterWarn.style.display = "";
    counterWarn.className = "counter-warn-strip warn";
    counterWarn.innerHTML =
      `${ICO_WARN_MD} <span>Este expediente supera <strong>1.000 páginas</strong>. ` +
      `El procesamiento puede tardar algunos segundos adicionales.</span>`;
  } else {
    counterWarn.style.display = "none";
  }
}

/* ═══════════════════════════════════════════════════════════════════════════
   Drag-and-drop reorder
   ═════════════════════════════════════════════════════════════════════════ */
function initDragSort() {
  let dragged = null;

  fileList.querySelectorAll(".file-item").forEach((item) => {
    item.addEventListener("dragstart", (e) => {
      dragged = item;
      item.classList.add("dragging");
      e.dataTransfer.effectAllowed = "move";
    });

    item.addEventListener("dragend", () => {
      item.classList.remove("dragging");
      fileList.querySelectorAll(".file-item").forEach((el) => {
        el.classList.remove("drag-over-top", "drag-over-bottom");
      });
      // Sync state from DOM order
      files = [...fileList.querySelectorAll(".file-item")].map((el) =>
        files.find((f) => f.id === el.dataset.id)
      ).filter(Boolean);
      renderList();
    });

    item.addEventListener("dragover", (e) => {
      e.preventDefault();
      if (!dragged || dragged === item) return;
      item.classList.remove("drag-over-top", "drag-over-bottom");
      const mid = item.getBoundingClientRect().top + item.offsetHeight / 2;
      if (e.clientY < mid) {
        item.classList.add("drag-over-top");
      } else {
        item.classList.add("drag-over-bottom");
      }
    });

    item.addEventListener("dragleave", () => {
      item.classList.remove("drag-over-top", "drag-over-bottom");
    });

    item.addEventListener("drop", (e) => {
      e.preventDefault();
      if (!dragged || dragged === item) return;
      item.classList.remove("drag-over-top", "drag-over-bottom");
      const mid = item.getBoundingClientRect().top + item.offsetHeight / 2;
      if (e.clientY < mid) {
        fileList.insertBefore(dragged, item);
      } else {
        fileList.insertBefore(dragged, item.nextSibling);
      }
    });
  });

  // Remove buttons
  fileList.querySelectorAll(".btn-remove").forEach((btn) => {
    btn.addEventListener("click", () => {
      const id = btn.dataset.id;
      files = files.filter((f) => f.id !== id);
      // fire-and-forget: tell backend to release temp file
      fetch(`${API}/api/files/${id}`, { method: "DELETE" }).catch(() => {});
      renderList();
    });
  });
}

/* ═══════════════════════════════════════════════════════════════════════════
   Upload helpers
   ═════════════════════════════════════════════════════════════════════════ */
async function uploadFile(file) {
  // Garantizar sesión activa antes de subir
  const sid = await ensureSession();

  const form = new FormData();
  form.append("file", file);
  const res = await fetch(
    `${API}/api/upload?session_id=${encodeURIComponent(sid)}`,
    { method: "POST", body: form }
  );
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || res.statusText);
  }
  const data = await res.json();
  _syncSession(data);   // adoptar sesión si el backend creó una nueva
  return data;
}

async function handleFileObjects(fileArray) {
  if (!fileArray.length) return;

  const supported = fileArray.filter((f) => {
    const ext = f.name.split(".").pop().toLowerCase();
    return _ALL_EXT.has(ext);
  });
  const skipped = fileArray.length - supported.length;
  if (skipped > 0) toast(`${skipped} archivo(s) ignorados (tipo no compatible)`, "warn");
  if (!supported.length) return;

  const existing = new Set(files.map((f) => f.name));
  const toUpload = supported.filter((f) => !existing.has(f.name));
  const dups = supported.length - toUpload.length;
  if (dups > 0) toast(`${dups} ya cargados, omitidos`, "warn");
  if (!toUpload.length) return;

  // 1. Add uploading placeholders immediately so the list updates right away
  const placeholders = toUpload.map((file) => ({
    id:       `_up_${Math.random().toString(36).slice(2)}`,
    name:     file.name,
    size:     file.size,
    pages:    0,
    error:    null,
    uploading: true,
    _ref:     file,           // keep reference to the original File object
  }));
  files.push(...placeholders);
  files = naturalSort(files);
  renderList();               // shows spinners in the list immediately

  // 2. Upload in chunks of 4
  let ok = 0;
  const chunks = chunkArray(placeholders, 4);

  for (const chunk of chunks) {
    const results = await Promise.allSettled(chunk.map((p) => uploadFile(p._ref)));

    results.forEach((r, ci) => {
      const ph  = chunk[ci];
      const idx = files.findIndex((f) => f.id === ph.id);
      if (idx === -1) return;

      if (r.status === "fulfilled") {
        files[idx] = r.value;   // replace placeholder with real server data
        ok++;
      } else {
        files.splice(idx, 1);   // remove failed placeholder
        toast(`Error subiendo "${ph.name}": ${r.reason.message}`, "error", 5000);
      }
    });

    // Re-render after each chunk so page counts appear progressively
    files = naturalSort(files);
    renderList();
  }

  if (ok > 0) toast(`${ok} archivo(s) cargado(s) correctamente`, "success");
}

function chunkArray(arr, size) {
  const out = [];
  for (let i = 0; i < arr.length; i += size) out.push(arr.slice(i, i + size));
  return out;
}

/* ═══════════════════════════════════════════════════════════════════════════
   Event listeners – upload
   ═════════════════════════════════════════════════════════════════════════ */

// Drag-and-drop onto the drop zone
dropZone.addEventListener("dragover", (e) => {
  e.preventDefault();
  dropZone.classList.add("drag-over");
});
dropZone.addEventListener("dragleave", () => dropZone.classList.remove("drag-over"));
dropZone.addEventListener("drop", (e) => {
  e.preventDefault();
  dropZone.classList.remove("drag-over");
  handleFileObjects([...e.dataTransfer.files]);
});
dropZone.addEventListener("click", () => fileInput.click());

// File picker
document.getElementById("btn-files").addEventListener("click", () => fileInput.click());
fileInput.addEventListener("change", () => {
  handleFileObjects([...fileInput.files]);
  fileInput.value = "";
});

// Folder picker (browser)
document.getElementById("btn-folder-browser").addEventListener("click", () =>
  folderInput.click()
);
folderInput.addEventListener("change", () => {
  handleFileObjects([...folderInput.files]);
  folderInput.value = "";
});

// Folder via text path (backend reads from disk)
document.getElementById("btn-load-folder").addEventListener("click", loadFolderByPath);
folderPath.addEventListener("keydown", (e) => {
  if (e.key === "Enter") loadFolderByPath();
});

async function loadFolderByPath() {
  const p = folderPath.value.trim();
  if (!p) { toast("Escribe la ruta de la carpeta primero", "warn"); return; }

  try {
    const res = await fetch(`${API}/api/load-folder`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ path: p }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      toast(err.detail || "Error cargando carpeta", "error");
      return;
    }
    // El backend devuelve {session_id, files}
    const { session_id: folderSession, files: loaded } = await res.json();

    // Adoptar la sesión creada por la carga de carpeta
    if (folderSession) currentSession = folderSession;

    // Deduplicar
    const existing = new Set(files.map((f) => f.name));
    let added = 0;
    loaded.forEach((f) => {
      if (!existing.has(f.name)) { files.push(f); added++; }
    });
    if (added === 0) {
      toast("No se agregaron archivos nuevos (ya estaban cargados)", "warn");
    } else {
      files = naturalSort(files);
      renderList();
      toast(`${added} archivo(s) cargados desde la carpeta`, "success");
    }
  } catch (e) {
    toast("Error de red al cargar carpeta", "error");
  }
}

/* ═══════════════════════════════════════════════════════════════════════════
   Sort & Clear
   ═════════════════════════════════════════════════════════════════════════ */
document.getElementById("btn-sort").addEventListener("click", () => {
  files = naturalSort(files);
  renderList();
  toast("Archivos ordenados por nombre natural", "success");
});

document.getElementById("btn-clear").addEventListener("click", () => {
  if (!files.length) return;
  if (!confirm("¿Eliminar todos los archivos cargados?")) return;
  fetch(`${API}/api/cleanup`, { method: "POST" }).catch(() => {});
  files = [];
  resetSession();
  renderList();
  resetResult();
});

/* ═══════════════════════════════════════════════════════════════════════════
   Generate
   ═════════════════════════════════════════════════════════════════════════ */
btnGenerate.addEventListener("click", generate);

async function generate() {
  if (!files.length) return;

  // Validar nombre obligatorio
  const outputName  = document.getElementById("cfg-output-name").value.trim();
  const nombreError = document.getElementById("nombre-error");
  if (!outputName) {
    if (nombreError) nombreError.style.display = "block";
    document.getElementById("cfg-output-name").focus();
    document.getElementById("cfg-output-name").scrollIntoView({ behavior: "smooth", block: "center" });
    return;
  }
  if (nombreError) nombreError.style.display = "none";

  const foliar = document.getElementById("cfg-foliar").checked;
  const config = {
    font_size:    parseFloat(document.getElementById("cfg-fontsize").value)    || 11,
    margin_top:   parseFloat(document.getElementById("cfg-margin-top").value)  || 20,
    margin_right: parseFloat(document.getElementById("cfg-margin-right").value)|| 30,
    position:     document.getElementById("cfg-position").value,
    foliar,
    folio_start:  Math.max(1, parseInt(document.getElementById("cfg-folio-start")?.value) || 1),
  };

  const body = {
    file_ids:          files.map((f) => f.id),
    config,
    output_name:       outputName,
    nombre_expediente: outputName,
  };

  setProcessing(true);
  resetResult();
  showProgress(true);
  setProgress(0, "Iniciando…");

  try {
    const res = await fetch(`${API}/api/process`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(err.detail || "Error al iniciar proceso");
    }
    const { task_id } = await res.json();
    startPolling(task_id);
  } catch (e) {
    setProcessing(false);
    showProgress(false);
    toast(`Error: ${e.message}`, "error", 6000);
  }
}

/* ═══════════════════════════════════════════════════════════════════════════
   Polling
   ═════════════════════════════════════════════════════════════════════════ */
function startPolling(taskId) {
  if (pollTimer) clearInterval(pollTimer);
  pollTimer = setInterval(() => pollTask(taskId), POLL_MS);
}

async function pollTask(taskId) {
  try {
    const res = await fetch(`${API}/api/task/${taskId}`);
    if (!res.ok) return;
    const task = await res.json();

    setProgress(task.progress, task.message);

    if (task.status === "done") {
      stopPolling();
      setProcessing(false);
      showProgress(false);
      resetSession();     // el backend ya limpió temp/; descartamos la referencia
      showResult(task);
    } else if (task.status === "error") {
      stopPolling();
      setProcessing(false);
      showProgress(false);
      resetSession();     // el backend también limpia en caso de error
      toast(`Error: ${task.error || task.message}`, "error", 8000);
    }
  } catch (_) { /* network hiccup – keep polling */ }
}

function stopPolling() {
  if (pollTimer) { clearInterval(pollTimer); pollTimer = null; }
}

/* ═══════════════════════════════════════════════════════════════════════════
   Progress UI
   ═════════════════════════════════════════════════════════════════════════ */
function showProgress(on) {
  progressSec.classList.toggle("visible", on);
}

function setProgress(pct, msg) {
  progressFill.style.width = `${pct}%`;
  progressPct.textContent  = `${Math.round(pct)}%`;
  progressMsg.textContent  = msg || "";
}

/* ═══════════════════════════════════════════════════════════════════════════
   Result UI
   ═════════════════════════════════════════════════════════════════════════ */
function showResult(task) {
  const fname = task.result_file;
  resultName.textContent = fname;
  resultMeta.textContent =
    `${task.total_pages} páginas foliadas • listo en expedientes_generados/`;

  btnDownload.href = `${API}/api/download/${encodeURIComponent(fname)}`;
  btnDownload.download = fname;

  if (task.failed_files && task.failed_files.length) {
    failedWarn.style.display = "";
    failedList.innerHTML = task.failed_files
      .map((f) => `<li>${esc(f)}</li>`)
      .join("");
  } else {
    failedWarn.style.display = "none";
  }

  resultSec.classList.add("visible");

  if (task.sin_registro) {
    toast(
      "Este expediente se generó sin registrar en el sistema por superar el límite diario del mismo nombre.",
      "warn",
      8000,
    );
  } else {
    toast(`¡Expediente listo! ${task.total_pages} páginas`, "success", 5000);
  }

  resultSec.scrollIntoView({ behavior: "smooth", block: "center" });

  if (task.total_mes !== undefined && task.total_mes !== null) {
    window.dispatchEvent(new CustomEvent("expediente-registrado", { detail: { total_mes: task.total_mes } }));
  }
}

function resetResult() {
  resultSec.classList.remove("visible");
  failedWarn.style.display = "none";
  failedList.innerHTML = "";
  btnDownload.href = "#";
}

/* ── Limpiar error de nombre al escribir ─────────────────────────────────── */
document.getElementById("cfg-output-name").addEventListener("input", () => {
  const err = document.getElementById("nombre-error");
  if (err) err.style.display = "none";
});

/* ── New expedition ───────────────────────────────────────────────────────── */
document.getElementById("btn-new").addEventListener("click", () => {
  fetch(`${API}/api/cleanup`, { method: "POST" }).catch(() => {});
  files = [];
  resetSession();
  renderList();
  resetResult();
  showProgress(false);
  document.getElementById("cfg-output-name").value = "";
  window.scrollTo({ top: 0, behavior: "smooth" });
});

/* ═══════════════════════════════════════════════════════════════════════════
   /api/count-pages  — server-side verification
   ═════════════════════════════════════════════════════════════════════════ */
async function callCountPages() {
  const readyIds = files.filter((f) => !f.uploading && f.id && !f.id.startsWith("_")).map((f) => f.id);
  if (!readyIds.length) {
    toast("No hay archivos listos para verificar", "warn");
    return;
  }

  const btn = document.getElementById("btn-recount");
  btn.disabled = true;
  btn.innerHTML = `<span class="spinner-sm"></span> Verificando…`;

  try {
    const res = await fetch(`${API}/api/count-pages`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ file_ids: readyIds }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(err.detail || res.statusText);
    }
    const data = await res.json();

    // Sync any server-corrected page counts back into local state
    let corrected = 0;
    data.files.forEach((sf) => {
      const local = files.find((f) => f.id === sf.id);
      if (local && sf.pages > 0 && sf.pages !== local.pages) {
        local.pages = sf.pages;
        corrected++;
      }
    });

    if (corrected > 0) {
      renderList();
      toast(`Conteo actualizado: ${corrected} archivo(s) corregido(s)`, "info");
    }
    toast(
      `Verificado: ${data.total_pages.toLocaleString("es")} páginas en ${readyIds.length} archivo(s)`,
      "success",
      4500
    );
  } catch (e) {
    toast(`Error al verificar: ${e.message}`, "error", 5000);
  } finally {
    btn.disabled = false;
    btn.innerHTML = `${ICO_REFRESH} Verificar`;
  }
}

document.getElementById("btn-recount").addEventListener("click", callCountPages);

/* ═══════════════════════════════════════════════════════════════════════════
   Folio toggle + preview
   ═════════════════════════════════════════════════════════════════════════ */
function updateFolioPreview() {
  const foliar     = document.getElementById("cfg-foliar").checked;
  const options    = document.getElementById("foliar-options");
  const previewSec = document.getElementById("folio-preview-section");
  const numEl      = document.getElementById("folio-num-preview");
  const infoEl     = document.getElementById("folio-preview-info");

  options.style.display    = foliar ? "" : "none";
  previewSec.style.display = foliar ? "" : "none";
  if (!foliar) return;

  const position   = document.getElementById("cfg-position").value;
  const fontSize   = parseFloat(document.getElementById("cfg-fontsize").value)    || 11;
  const mTop       = parseFloat(document.getElementById("cfg-margin-top").value)  || 20;
  const mRight     = parseFloat(document.getElementById("cfg-margin-right").value)|| 30;
  const folioStart = Math.max(1, parseInt(document.getElementById("cfg-folio-start")?.value) || 1);

  // Scale: preview page is ~85px wide vs real Oficio ~612pt
  const scale = 85 / 612;
  numEl.style.fontSize = `${Math.max(7, Math.round(fontSize * scale * 6))}px`;
  numEl.style.top      = position.startsWith("top")    ? `${Math.round(mTop   * scale)}px` : "auto";
  numEl.style.bottom   = position.startsWith("bottom") ? `${Math.round(mTop   * scale)}px` : "auto";
  numEl.style.right    = position.endsWith("right")    ? `${Math.round(mRight * scale)}px` : "auto";
  numEl.style.left     = position.endsWith("left")     ? `${Math.round(mRight * scale)}px` : "auto";
  numEl.textContent    = String(folioStart).padStart(3, "0");

  const posLabel = {
    "top-right":    "Arriba derecha",
    "top-left":     "Arriba izquierda",
    "bottom-right": "Abajo derecha",
    "bottom-left":  "Abajo izquierda",
  }[position] || position;

  infoEl.innerHTML = `
    <div class="folio-preview-row"><span>Posición</span><strong>${posLabel}</strong></div>
    <div class="folio-preview-row"><span>Tamaño letra</span><strong>${fontSize} pt</strong></div>
    <div class="folio-preview-row"><span>Márgenes</span><strong>${mTop} pt / ${mRight} pt</strong></div>
    <div class="folio-preview-row"><span>Primer folio</span><strong>${folioStart}</strong></div>
  `;
}

["cfg-foliar","cfg-position","cfg-fontsize","cfg-margin-top","cfg-margin-right","cfg-folio-start"].forEach((id) => {
  const el = document.getElementById(id);
  if (el) {
    el.addEventListener("change", updateFolioPreview);
    el.addEventListener("input",  updateFolioPreview);
  }
});
updateFolioPreview();

/* ── Init ─────────────────────────────────────────────────────────────────── */
renderList();
