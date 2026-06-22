"use strict";

const API     = "";
const POLL_MS = 700;

/* ── SVG icons ───────────────────────────────────────────────────────────── */
var ICO_FILE  = `<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>`;
var ICO_IMAGE = `<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="18" height="18" rx="2" ry="2"/><circle cx="8.5" cy="8.5" r="1.5"/><polyline points="21 15 16 10 5 21"/></svg>`;
var ICO_WORD  = `<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/><line x1="10" y1="9" x2="8" y2="9"/></svg>`;
var ICO_GRIP  = `<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="9" cy="5" r="1"/><circle cx="9" cy="12" r="1"/><circle cx="9" cy="19" r="1"/><circle cx="15" cy="5" r="1"/><circle cx="15" cy="12" r="1"/><circle cx="15" cy="19" r="1"/></svg>`;
var ICO_ZAP   = `<svg xmlns="http://www.w3.org/2000/svg" width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg>`;
var ICO_UPLOAD= `<svg xmlns="http://www.w3.org/2000/svg" width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/></svg>`;
var ICO_OK_TOAST   = `<svg xmlns="http://www.w3.org/2000/svg" width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>`;
var ICO_ERR_TOAST  = `<svg xmlns="http://www.w3.org/2000/svg" width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>`;
var ICO_WARN_TOAST = `<svg xmlns="http://www.w3.org/2000/svg" width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>`;
var ICO_INFO_TOAST = `<svg xmlns="http://www.w3.org/2000/svg" width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>`;

/* ── Estado global ───────────────────────────────────────────────────────── */
let selectedExp    = null;   // nombre del expediente activo
let expFiles       = [];     // archivos del expediente activo (desde API)
let allExpedientes = [];     // lista completa para búsqueda local
let pollTimer      = null;
let activeTaskId   = null;
let _autoSaveTimer = null;   // debounce para auto-guardar config folio

/* ═══════════════════════════════════════════════════════════════════════════
   Helpers
   ═════════════════════════════════════════════════════════════════════════ */
function esc(s) {
  return String(s)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function fmtSize(bytes) {
  if (bytes < 1024)    return bytes + " B";
  if (bytes < 1048576) return (bytes / 1024).toFixed(1) + " KB";
  return (bytes / 1048576).toFixed(1) + " MB";
}

function estimateTime(pages, fileCount) {
  if (pages === 0) return null;
  const secs = Math.max(2, Math.ceil(pages / 150) + Math.ceil(fileCount * 0.5));
  return secs < 60 ? `~${secs}s` : `~${Math.ceil(secs / 60)} min`;
}

function toast(msg, type = "info", dur = 3500) {
  const icons = { success: ICO_OK_TOAST, error: ICO_ERR_TOAST, warn: ICO_WARN_TOAST, info: ICO_INFO_TOAST };
  const t = document.createElement("div");
  t.className = `toast ${type}`;
  t.innerHTML = `<span class="toast-icon">${icons[type] || ICO_INFO_TOAST}</span><span class="toast-msg">${msg}</span>`;
  document.getElementById("toast-container").append(t);
  setTimeout(() => t.remove(), dur);
}

function fileIcon(name) {
  const ext = name.split(".").pop().toLowerCase();
  if (["jpg","jpeg","png","gif","bmp","tiff","webp"].includes(ext)) return ICO_IMAGE;
  if (["docx","doc"].includes(ext)) return ICO_WORD;
  return ICO_FILE;
}

/* ═══════════════════════════════════════════════════════════════════════════
   Init — punto de entrada llamado desde el inline script de index.html
   ═════════════════════════════════════════════════════════════════════════ */
async function initApp() {
  document.getElementById("layout-wrap").style.display = "flex";
  try {
    const r = await fetch(`${API}/api/config`);
    if (r.ok) {
      const cfg = await r.json();
      if (!cfg.configurada && cfg.carpeta_raiz) {
        fetch(`${API}/api/config`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ carpeta_raiz: cfg.carpeta_raiz }),
        }).catch(() => {});
      }
    }
  } catch {}
  await loadExpediciones();
}

/* ═══════════════════════════════════════════════════════════════════════════
   Sidebar — lista de expedientes
   ═════════════════════════════════════════════════════════════════════════ */
async function loadExpediciones() {
  try {
    const r = await fetch(`${API}/api/expedientes`);
    if (r.ok) allExpedientes = await r.json();
    else      allExpedientes = [];
  } catch { allExpedientes = []; }
  renderExpList();
}

function renderExpList() {
  const q = (document.getElementById("exp-search").value || "").toLowerCase();
  const filtrados = allExpedientes.filter(e => e.nombre.toLowerCase().includes(q));
  const ul = document.getElementById("exp-list");
  ul.innerHTML = "";

  if (!filtrados.length) {
    const li = document.createElement("li");
    li.className = "exp-list-empty";
    li.textContent = allExpedientes.length ? "Sin resultados" : "Sin expedientes aún";
    ul.append(li);
    return;
  }

  filtrados.forEach(exp => {
    const li = document.createElement("li");
    li.className = "exp-item" + (selectedExp === exp.nombre ? " active" : "");
    li.innerHTML = `
      <span class="exp-item-dot"></span>
      <span class="exp-item-name" title="${esc(exp.nombre)}">${esc(exp.nombre)}</span>
      <button class="exp-item-del" title="Ocultar expediente" data-nombre="${esc(exp.nombre)}">✕</button>
    `;
    li.addEventListener("click", e => {
      if (!e.target.closest(".exp-item-del")) selectExpediente(exp.nombre);
    });
    li.querySelector(".exp-item-del").addEventListener("click", async e => {
      e.stopPropagation();
      if (!confirm(`¿Ocultar "${exp.nombre}" de la lista?\nLos archivos se conservan en disco.`)) return;
      if (selectedExp === exp.nombre) deselectExpediente();
      try {
        await fetch(`${API}/api/expedientes/${encodeURIComponent(exp.nombre)}`, { method: "DELETE" });
        await loadExpediciones();
      } catch (err) { toast("Error al ocultar: " + err.message, "error"); }
    });
    ul.append(li);
  });
}

/* ── Crear expediente ─────────────────────────────────────────────────────── */
function _showCreateForm() {
  document.getElementById("exp-create-form").style.display = "flex";
  document.getElementById("exp-new-name").value = "";
  document.getElementById("exp-new-name").focus();
}

function _hideCreateForm() {
  document.getElementById("exp-create-form").style.display = "none";
}

async function _doCreateExpediente() {
  const nombre = document.getElementById("exp-new-name").value.trim();
  if (!nombre) { document.getElementById("exp-new-name").focus(); return; }
  try {
    const r = await fetch(`${API}/api/expedientes`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ nombre }),
    });
    if (!r.ok) {
      const e = await r.json().catch(() => ({}));
      toast(e.detail || "Error al crear expediente", "error");
      return;
    }
    _hideCreateForm();
    await loadExpediciones();
    await selectExpediente(nombre);
    toast(`Expediente "${nombre}" creado`, "success", 2500);
  } catch (err) { toast("Error: " + err.message, "error"); }
}

/* ═══════════════════════════════════════════════════════════════════════════
   Panel derecho — selección y detalle de expediente
   ═════════════════════════════════════════════════════════════════════════ */
async function selectExpediente(nombre) {
  selectedExp = nombre;
  renderExpList();
  _showExpDetail(nombre);
  await loadExpFiles();
}

function deselectExpediente() {
  selectedExp = null;
  expFiles    = [];
  renderExpList();
  _showExpEmpty();
  stopPolling();
  resetResult();
}

function _showExpEmpty() {
  document.getElementById("empty-state").style.display  = "";
  document.getElementById("exp-detail").style.display   = "none";
}

function _showExpDetail(nombre) {
  document.getElementById("empty-state").style.display  = "none";
  document.getElementById("exp-detail").style.display   = "grid";
  document.getElementById("exp-nombre").textContent     = nombre;
  document.getElementById("cfg-output-name").value      = nombre;
  resetResult();
  showProgress(false);
}

/* ── Cargar archivos del expediente ──────────────────────────────────────── */
async function loadExpFiles() {
  if (!selectedExp) return;
  try {
    const r = await fetch(`${API}/api/expedientes/${encodeURIComponent(selectedExp)}/archivos`);
    if (r.ok) {
      const d = await r.json();
      expFiles = d.archivos ?? [];
      applyFolioConfig(d.config_folio ?? {});
    } else {
      expFiles = [];
    }
  } catch { expFiles = []; }
  renderExpFiles();
  updateExpHeader();
}

function updateExpHeader() {
  const count = expFiles.length;
  const pages = expFiles.reduce((s, f) => s + (f.paginas || 0), 0);

  document.getElementById("exp-meta").textContent =
    `${count} archivo${count !== 1 ? "s" : ""} · ${pages} página${pages !== 1 ? "s" : ""}`;

  const t = estimateTime(pages, count);
  document.getElementById("exp-summary").innerHTML = count === 0
    ? "Agrega archivos al expediente para continuar."
    : `<strong>${count}</strong> archivo${count !== 1 ? "s" : ""} · ` +
      `<strong>${pages}</strong> página${pages !== 1 ? "s" : ""}` +
      (t ? ` · tiempo estimado: <strong>${t}</strong>` : "") +
      ` · puedes reordenar arrastrando las filas.`;

  const btn = document.getElementById("btn-generate");
  btn.disabled = count === 0;
  btn.innerHTML = count === 0
    ? `${ICO_UPLOAD} Agrega archivos para continuar`
    : `${ICO_ZAP} Generar expediente`;
}

function renderExpFiles() {
  const ul    = document.getElementById("exp-file-list");
  const empty = document.getElementById("exp-file-empty");
  ul.innerHTML = "";

  if (!expFiles.length) {
    empty.style.display = "";
    return;
  }
  empty.style.display = "none";

  expFiles.forEach((f, i) => {
    const li = document.createElement("li");
    li.className      = "exp-file-item";
    li.dataset.nombre = f.nombre;
    li.draggable      = true;
    li.innerHTML = `
      <span class="exp-file-handle">${ICO_GRIP}</span>
      <span class="exp-file-num">${i + 1}</span>
      <span class="file-icon">${fileIcon(f.nombre)}</span>
      <div class="exp-file-info">
        <div class="exp-file-name" title="${esc(f.nombre)}">${esc(f.nombre)}</div>
        ${f.paginas ? `<div class="exp-file-meta"><span class="pages-badge">${f.paginas} págs.</span></div>` : ""}
      </div>
      <button class="exp-file-remove" title="Eliminar" data-nombre="${esc(f.nombre)}">✕</button>
    `;
    ul.append(li);
  });

  _initExpDragSort();

  ul.querySelectorAll(".exp-file-remove").forEach(btn => {
    btn.addEventListener("click", async () => {
      const nombre = btn.dataset.nombre;
      if (!confirm(`¿Eliminar "${nombre}" del expediente?\nEl archivo se borrará del disco.`)) return;
      try {
        await fetch(
          `${API}/api/expedientes/${encodeURIComponent(selectedExp)}/archivos/${encodeURIComponent(nombre)}`,
          { method: "DELETE" }
        );
        await loadExpFiles();
      } catch (err) { toast("Error al eliminar: " + err.message, "error"); }
    });
  });
}

/* ── Drag-sort de archivos ───────────────────────────────────────────────── */
function _initExpDragSort() {
  const ul = document.getElementById("exp-file-list");
  let dragged = null;

  ul.querySelectorAll(".exp-file-item").forEach(item => {
    item.addEventListener("dragstart", () => {
      dragged = item;
      setTimeout(() => { item.style.opacity = ".35"; }, 0);
    });
    item.addEventListener("dragend", () => {
      item.style.opacity = "";
      dragged = null;
      _renumberExpFiles();
      _saveOrden();
    });
    item.addEventListener("dragover", e => e.preventDefault());
    item.addEventListener("drop", () => {
      if (!dragged || dragged === item) return;
      const all = [...ul.children];
      if (all.indexOf(dragged) < all.indexOf(item)) {
        ul.insertBefore(dragged, item.nextSibling);
      } else {
        ul.insertBefore(dragged, item);
      }
    });
  });
}

function _renumberExpFiles() {
  document.querySelectorAll("#exp-file-list .exp-file-num").forEach((el, i) => {
    el.textContent = i + 1;
  });
}

async function _saveOrden() {
  if (!selectedExp) return;
  const orden = [...document.querySelectorAll("#exp-file-list .exp-file-item")]
    .map(li => li.dataset.nombre);
  await fetch(`${API}/api/expedientes/${encodeURIComponent(selectedExp)}/orden`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ orden }),
  }).catch(() => {});
}

/* ── Agregar archivos al expediente ──────────────────────────────────────── */
async function addFilesToExp(fileList) {
  if (!selectedExp || !fileList.length) return;
  toast(`Agregando ${fileList.length} archivo(s)…`, "info", 2000);
  for (const file of fileList) {
    await _uploadToExp(file, false);
  }
  await loadExpFiles();
}

async function _uploadToExp(file, replace = false) {
  const fd  = new FormData();
  fd.append("file", file);
  const url = `${API}/api/expedientes/${encodeURIComponent(selectedExp)}/archivos`
    + (replace ? "?replace=true" : "");
  try {
    const r = await fetch(url, { method: "POST", body: fd });
    if (r.status === 409) {
      if (confirm(`"${file.name}" ya existe. ¿Reemplazar?`)) {
        await _uploadToExp(file, true);
      }
    } else if (!r.ok) {
      const e = await r.json().catch(() => ({}));
      toast(`Error con "${file.name}": ${e.detail || r.status}`, "error");
    }
  } catch (err) {
    toast("Error: " + err.message, "error");
  }
}

/* ═══════════════════════════════════════════════════════════════════════════
   Config folio — apply + auto-save con debounce
   ═════════════════════════════════════════════════════════════════════════ */
function applyFolioConfig(cfg) {
  const s = (id, val) => { const el = document.getElementById(id); if (el && val !== undefined) el.value = val; };
  const c = (id, val) => { const el = document.getElementById(id); if (el && val !== undefined) el.checked = !!val; };
  c("cfg-foliar",       cfg.activo);
  s("cfg-position",     cfg.posicion);
  s("cfg-fontsize",     cfg.tamano);
  s("cfg-margin-top",   cfg.margen_superior);
  s("cfg-margin-right", cfg.margen_lateral);
  s("cfg-folio-start",  cfg.iniciar_desde);
  updateFolioPreview();
}

function _scheduleSaveFolioCfg() {
  clearTimeout(_autoSaveTimer);
  _autoSaveTimer = setTimeout(_saveFolioConfig, 500);
}

async function _saveFolioConfig() {
  if (!selectedExp) return;
  const cfg = {
    activo:          document.getElementById("cfg-foliar").checked,
    posicion:        document.getElementById("cfg-position").value,
    tamano:          parseFloat(document.getElementById("cfg-fontsize").value)    || 11,
    margen_superior: parseFloat(document.getElementById("cfg-margin-top").value)  || 20,
    margen_lateral:  parseFloat(document.getElementById("cfg-margin-right").value)|| 30,
    iniciar_desde:   Math.max(1, parseInt(document.getElementById("cfg-folio-start").value) || 1),
  };
  await fetch(`${API}/api/expedientes/${encodeURIComponent(selectedExp)}/config`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(cfg),
  }).catch(() => {});
}

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
  const folioStart = Math.max(1, parseInt(document.getElementById("cfg-folio-start").value) || 1);

  const scale = 85 / 612;
  numEl.style.fontSize = `${Math.max(7, Math.round(fontSize * scale * 6))}px`;
  numEl.style.top    = position.startsWith("top")    ? `${Math.round(mTop   * scale)}px` : "auto";
  numEl.style.bottom = position.startsWith("bottom") ? `${Math.round(mTop   * scale)}px` : "auto";
  numEl.style.right  = position.endsWith("right")    ? `${Math.round(mRight * scale)}px` : "auto";
  numEl.style.left   = position.endsWith("left")     ? `${Math.round(mRight * scale)}px` : "auto";
  numEl.textContent  = String(folioStart).padStart(3, "0");

  const posLabel = {
    "top-right": "Arriba derecha", "top-left": "Arriba izquierda",
    "bottom-right": "Abajo derecha", "bottom-left": "Abajo izquierda",
  }[position] || position;

  infoEl.innerHTML = `
    <div class="folio-preview-row"><span>Posición</span><strong>${posLabel}</strong></div>
    <div class="folio-preview-row"><span>Tamaño letra</span><strong>${fontSize} pt</strong></div>
    <div class="folio-preview-row"><span>Márgenes</span><strong>${mTop} pt / ${mRight} pt</strong></div>
    <div class="folio-preview-row"><span>Primer folio</span><strong>${folioStart}</strong></div>
  `;
}

/* ═══════════════════════════════════════════════════════════════════════════
   Generar expediente
   ═════════════════════════════════════════════════════════════════════════ */
async function generate() {
  if (!selectedExp || expFiles.length === 0) return;

  const outputName  = document.getElementById("cfg-output-name").value.trim();
  const nombreError = document.getElementById("nombre-error");
  if (!outputName) {
    nombreError.style.display = "block";
    document.getElementById("cfg-output-name").focus();
    document.getElementById("cfg-output-name").scrollIntoView({ behavior: "smooth", block: "center" });
    return;
  }
  nombreError.style.display = "none";

  const config_folio = {
    activo:          document.getElementById("cfg-foliar").checked,
    posicion:        document.getElementById("cfg-position").value,
    tamano:          parseFloat(document.getElementById("cfg-fontsize").value)    || 11,
    margen_superior: parseFloat(document.getElementById("cfg-margin-top").value)  || 20,
    margen_lateral:  parseFloat(document.getElementById("cfg-margin-right").value)|| 30,
    iniciar_desde:   Math.max(1, parseInt(document.getElementById("cfg-folio-start").value) || 1),
  };

  _setProcessing(true);
  resetResult();
  showProgress(true);
  setProgress(0, "Iniciando…");

  try {
    const r = await fetch(
      `${API}/api/expedientes/${encodeURIComponent(selectedExp)}/generar`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ output_name: outputName, config_folio }),
      }
    );
    if (!r.ok) {
      const err = await r.json().catch(() => ({ detail: r.statusText }));
      throw new Error(err.detail || "Error al generar");
    }
    const { task_id } = await r.json();
    activeTaskId = task_id;
    startPolling(task_id);
  } catch (e) {
    _setProcessing(false);
    showProgress(false);
    toast(`Error: ${e.message}`, "error", 6000);
  }
}

/* ═══════════════════════════════════════════════════════════════════════════
   Polling de progreso
   ═════════════════════════════════════════════════════════════════════════ */
function startPolling(taskId) {
  if (pollTimer) clearInterval(pollTimer);
  pollTimer = setInterval(() => _pollTask(taskId), POLL_MS);
}

async function _pollTask(taskId) {
  try {
    const r = await fetch(`${API}/api/task/${taskId}`);
    if (!r.ok) return;
    const task = await r.json();
    setProgress(task.progress, task.message);
    if (task.status === "done") {
      stopPolling();
      _setProcessing(false);
      showProgress(false);
      showResult(task);
    } else if (task.status === "error") {
      stopPolling();
      _setProcessing(false);
      showProgress(false);
      toast(`Error: ${task.error || task.message}`, "error", 8000);
    }
  } catch { /* network hiccup — keep polling */ }
}

function stopPolling() {
  if (pollTimer) { clearInterval(pollTimer); pollTimer = null; }
  activeTaskId = null;
}

async function cancelGeneration() {
  const tid = activeTaskId;
  if (!tid) return;
  document.getElementById("btn-cancel-gen").disabled = true;
  try { await fetch(`${API}/api/task/${tid}`, { method: "DELETE" }); } catch {}
  stopPolling();
  _setProcessing(false);
  showProgress(false);
  toast("Generación cancelada", "warn", 4000);
}

/* ═══════════════════════════════════════════════════════════════════════════
   UI: progreso, resultado
   ═════════════════════════════════════════════════════════════════════════ */
function showProgress(on) {
  document.getElementById("progress-section").classList.toggle("visible", on);
  document.getElementById("btn-cancel-gen").disabled = !on;
}

function setProgress(pct, msg) {
  document.getElementById("progress-fill").style.width = `${pct}%`;
  document.getElementById("progress-pct").textContent  = `${Math.round(pct)}%`;
  document.getElementById("progress-msg").textContent  = msg || "";
}

function _setProcessing(on) {
  const btn = document.getElementById("btn-generate");
  btn.disabled = on || expFiles.length === 0;
  if (on) {
    btn.innerHTML = `<span class="spinner"></span> Procesando…`;
  } else {
    updateExpHeader();
  }
}

function showResult(task) {
  const fname = task.result_file;
  document.getElementById("result-name").textContent = fname;
  const secs = task.elapsed_seconds != null ? ` · generado en ${task.elapsed_seconds}s` : "";
  document.getElementById("result-meta").textContent =
    `${task.total_pages} páginas foliadas${secs}`;

  const dlBtn   = document.getElementById("btn-download");
  dlBtn.href    = `${API}/api/download/${encodeURIComponent(fname)}`;
  dlBtn.download = fname;

  if (task.failed_files && task.failed_files.length) {
    document.getElementById("failed-warn").style.display = "";
    document.getElementById("failed-list").innerHTML = task.failed_files
      .map(f => `<li>${esc(f)}</li>`).join("");
  } else {
    document.getElementById("failed-warn").style.display = "none";
  }

  document.getElementById("result-section").classList.add("visible");

  if (task.sin_registro) {
    toast("Este expediente se generó sin registrar por superar el límite diario del mismo nombre.", "warn", 8000);
  } else {
    const secsLabel = task.elapsed_seconds != null ? ` en ${task.elapsed_seconds}s` : "";
    toast(`¡Expediente listo! ${task.total_pages} páginas${secsLabel}`, "success", 5000);
  }

  document.getElementById("result-section").scrollIntoView({ behavior: "smooth", block: "center" });

  if (task.total_mes !== undefined && task.total_mes !== null) {
    window.dispatchEvent(new CustomEvent("expediente-registrado", { detail: { total_mes: task.total_mes } }));
  }
}

function resetResult() {
  document.getElementById("result-section").classList.remove("visible");
  document.getElementById("failed-warn").style.display = "none";
  document.getElementById("failed-list").innerHTML     = "";
  document.getElementById("btn-download").href         = "#";
}

/* ═══════════════════════════════════════════════════════════════════════════
   Event listeners
   ═════════════════════════════════════════════════════════════════════════ */

// Sidebar
document.getElementById("btn-new-exp").addEventListener("click", _showCreateForm);
document.getElementById("btn-exp-create-cancel").addEventListener("click", _hideCreateForm);
document.getElementById("btn-exp-create-ok").addEventListener("click", _doCreateExpediente);
document.getElementById("exp-new-name").addEventListener("keydown", e => {
  if (e.key === "Enter")  _doCreateExpediente();
  if (e.key === "Escape") _hideCreateForm();
});
document.getElementById("exp-search").addEventListener("input", renderExpList);

// Panel derecho
document.getElementById("btn-close-exp").addEventListener("click", deselectExpediente);
document.getElementById("btn-add-files").addEventListener("click", () => {
  document.getElementById("exp-file-input").click();
});
document.getElementById("exp-file-input").addEventListener("change", async e => {
  const files = [...e.target.files];
  e.target.value = "";
  await addFilesToExp(files);
});

// Folio config — preview inmediato + auto-guardar con debounce
["cfg-foliar","cfg-position","cfg-fontsize","cfg-margin-top","cfg-margin-right","cfg-folio-start"].forEach(id => {
  const el = document.getElementById(id);
  if (!el) return;
  el.addEventListener("change", () => { updateFolioPreview(); _scheduleSaveFolioCfg(); });
  el.addEventListener("input",  () => { updateFolioPreview(); _scheduleSaveFolioCfg(); });
});

// Nombre del PDF — limpiar error al escribir
document.getElementById("cfg-output-name").addEventListener("input", () => {
  document.getElementById("nombre-error").style.display = "none";
});

// Generar
document.getElementById("btn-generate").addEventListener("click", generate);

// Cancelar
document.getElementById("btn-cancel-gen").addEventListener("click", cancelGeneration);

// Generar de nuevo — oculta resultado, mantiene expediente abierto
document.getElementById("btn-new").addEventListener("click", () => {
  resetResult();
  showProgress(false);
  updateExpHeader();
});

// Init folio preview
updateFolioPreview();
