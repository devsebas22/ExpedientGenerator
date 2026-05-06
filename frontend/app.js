"use strict";
/* ═══════════════════════════════════════════════════════════════════════════
   Expediente Digital – frontend logic
   ═════════════════════════════════════════════════════════════════════════ */

const API = "";          // same origin
const POLL_MS = 700;     // progress poll interval

/* ── State ──────────────────────────────────────────────────────────────── */
// [{id, name, size, pages, error}]  — ordered as the user sees them
let files = [];
let pollTimer = null;

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
  const t = document.createElement("div");
  t.className = `toast ${type}`;
  t.textContent = msg;
  document.getElementById("toast-container").append(t);
  setTimeout(() => t.remove(), dur);
}

function setProcessing(on) {
  btnGenerate.disabled = on || files.length === 0;
  btnGenerate.innerHTML = on
    ? `<span class="spinner"></span> Procesando…`
    : "⚡ Generar expediente";
}

/* ═══════════════════════════════════════════════════════════════════════════
   Render file list
   ═════════════════════════════════════════════════════════════════════════ */
function renderList() {
  fileList.innerHTML = "";

  files.forEach((f, i) => {
    const li = document.createElement("li");
    li.className = "file-item";
    li.draggable = true;
    li.dataset.id = f.id;

    const pagesHtml = f.pages > 0
      ? `<span class="pages-badge">${f.pages} págs.</span>`
      : `<span class="err">⚠ Error leyendo páginas</span>`;

    li.innerHTML = `
      <span class="handle">⠿</span>
      <span class="file-num">${i + 1}</span>
      <span class="file-icon">📄</span>
      <div class="file-info">
        <div class="file-name" title="${esc(f.name)}">${esc(f.name)}</div>
        <div class="file-meta">${pagesHtml}${esc(fmtSize(f.size))}</div>
      </div>
      <button class="btn-remove" title="Eliminar" data-id="${f.id}">✕</button>
    `;

    fileList.append(li);
  });

  initDragSort();
  updateBadges();
}

function esc(s) {
  return String(s)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function updateBadges() {
  const total = files.reduce((s, f) => s + (f.pages > 0 ? f.pages : 0), 0);
  badgeFiles.textContent = `${files.length} archivo${files.length !== 1 ? "s" : ""}`;
  badgePages.textContent = `${total} página${total !== 1 ? "s" : ""}`;

  btnGenerate.disabled = files.length === 0;

  if (files.length === 0) {
    actionSummary.innerHTML = "Carga al menos un PDF para continuar.";
  } else {
    actionSummary.innerHTML = `
      <strong>${files.length}</strong> archivo${files.length !== 1 ? "s" : ""} •
      <strong>${total}</strong> página${total !== 1 ? "s" : ""} en total.
      Puedes reordenar arrastrando las filas.
    `;
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
  const form = new FormData();
  form.append("file", file);
  const res = await fetch(`${API}/api/upload`, { method: "POST", body: form });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || res.statusText);
  }
  return res.json();
}

async function handleFileObjects(fileArray) {
  if (!fileArray.length) return;

  // Filter only PDFs
  const pdfs = fileArray.filter((f) => f.name.toLowerCase().endsWith(".pdf"));
  const skipped = fileArray.length - pdfs.length;
  if (skipped > 0) toast(`${skipped} archivo(s) ignorados (no son PDF)`, "warn");
  if (!pdfs.length) return;

  // Deduplicate by name (don't re-upload already loaded files)
  const existing = new Set(files.map((f) => f.name));
  const toUpload = pdfs.filter((f) => !existing.has(f.name));
  const dups = pdfs.length - toUpload.length;
  if (dups > 0) toast(`${dups} archivo(s) ya estaban cargados, omitidos`, "warn");
  if (!toUpload.length) return;

  toast(`Subiendo ${toUpload.length} archivo(s)…`, "info", 2000);
  let ok = 0;
  let fail = 0;

  // Upload concurrently (max 4 at a time)
  const chunks = chunkArray(toUpload, 4);
  for (const chunk of chunks) {
    const results = await Promise.allSettled(chunk.map(uploadFile));
    results.forEach((r, i) => {
      if (r.status === "fulfilled") {
        files.push(r.value);
        ok++;
      } else {
        console.error(chunk[i].name, r.reason);
        toast(`Error subiendo "${chunk[i].name}": ${r.reason.message}`, "error", 5000);
        fail++;
      }
    });
  }

  // Auto natural-sort after upload
  files = naturalSort(files);
  renderList();

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
    const loaded = await res.json();
    // Deduplicate
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
  renderList();
  resetResult();
});

/* ═══════════════════════════════════════════════════════════════════════════
   Generate
   ═════════════════════════════════════════════════════════════════════════ */
btnGenerate.addEventListener("click", generate);

async function generate() {
  if (!files.length) return;

  const config = {
    font_size:    parseFloat(document.getElementById("cfg-fontsize").value)    || 11,
    margin_top:   parseFloat(document.getElementById("cfg-margin-top").value)  || 20,
    margin_right: parseFloat(document.getElementById("cfg-margin-right").value)|| 30,
    position:     document.getElementById("cfg-position").value,
  };
  const outputName = document.getElementById("cfg-output-name").value.trim();

  const body = {
    file_ids:    files.map((f) => f.id),
    config,
    output_name: outputName || null,
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
      showResult(task);
    } else if (task.status === "error") {
      stopPolling();
      setProcessing(false);
      showProgress(false);
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
  toast(`¡Expediente listo! ${task.total_pages} páginas`, "success", 5000);
  resultSec.scrollIntoView({ behavior: "smooth", block: "center" });
}

function resetResult() {
  resultSec.classList.remove("visible");
  failedWarn.style.display = "none";
  failedList.innerHTML = "";
  btnDownload.href = "#";
}

/* ── New expedition ───────────────────────────────────────────────────────── */
document.getElementById("btn-new").addEventListener("click", () => {
  fetch(`${API}/api/cleanup`, { method: "POST" }).catch(() => {});
  files = [];
  renderList();
  resetResult();
  showProgress(false);
  document.getElementById("cfg-output-name").value = "";
  window.scrollTo({ top: 0, behavior: "smooth" });
});

/* ── Init ─────────────────────────────────────────────────────────────────── */
renderList();
