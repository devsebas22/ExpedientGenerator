"use strict";
/* ═══════════════════════════════════════════════════════════════════════════
   Expediente Digital — App logic (two-panel layout)
   ═════════════════════════════════════════════════════════════════════════ */

const API      = "";
const POLL_MS  = 700;

/* ── SVG icons ───────────────────────────────────────────────────────────── */
const ICO_FILE  = `<svg xmlns="http://www.w3.org/2000/svg" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>`;
const ICO_IMAGE = `<svg xmlns="http://www.w3.org/2000/svg" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="18" height="18" rx="2" ry="2"/><circle cx="8.5" cy="8.5" r="1.5"/><polyline points="21 15 16 10 5 21"/></svg>`;
const ICO_WORD  = `<svg xmlns="http://www.w3.org/2000/svg" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/></svg>`;
const ICO_GRIP  = `<svg xmlns="http://www.w3.org/2000/svg" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="9" cy="5" r="1"/><circle cx="9" cy="12" r="1"/><circle cx="9" cy="19" r="1"/><circle cx="15" cy="5" r="1"/><circle cx="15" cy="12" r="1"/><circle cx="15" cy="19" r="1"/></svg>`;
const ICO_ZAP   = `<svg xmlns="http://www.w3.org/2000/svg" width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg>`;
const ICO_OK_T  = `<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>`;
const ICO_ERR_T = `<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>`;
const ICO_WARN_T= `<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>`;
const ICO_INFO_T= `<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>`;

/* ── State ───────────────────────────────────────────────────────────────── */
let expediciones    = [];   // [{nombre, archivos, creado}]
let selectedNombre  = null; // nombre del expediente activo
let archivos        = [];   // [{nombre, paginas, tamanio, error}] del expediente activo
let pollTimer       = null;
let activeTaskId    = null;
let ctxNombre       = null; // expedition in context menu

/* ── File types ──────────────────────────────────────────────────────────── */
const _IMG_EXT  = new Set(["jpg","jpeg","png","gif","bmp","tiff","webp"]);
const _WORD_EXT = new Set(["docx","doc"]);
const _ALL_EXT  = new Set([..._IMG_EXT, ..._WORD_EXT, "pdf"]);

function fileIcon(name) {
  const ext = (name.split(".").pop() || "").toLowerCase();
  if (_IMG_EXT.has(ext))  return ICO_IMAGE;
  if (_WORD_EXT.has(ext)) return ICO_WORD;
  return ICO_FILE;
}

function esc(s) {
  return String(s)
    .replace(/&/g, "&amp;").replace(/</g, "&lt;")
    .replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}

function enc(s) { return encodeURIComponent(s); }

/* ── Toast ───────────────────────────────────────────────────────────────── */
function toast(msg, type = "info", dur = 3500) {
  const icons = { success: ICO_OK_T, error: ICO_ERR_T, warn: ICO_WARN_T, info: ICO_INFO_T };
  const t = document.createElement("div");
  t.className = `toast ${type}`;
  t.innerHTML = `<span class="toast-icon">${icons[type] || ICO_INFO_T}</span><span class="toast-msg">${esc(msg)}</span>`;
  document.getElementById("toast-container").append(t);
  setTimeout(() => t.remove(), dur);
}

/* ── Wait for app ready ──────────────────────────────────────────────────── */
function whenReady(fn) {
  if (window.appReady) { fn(); }
  else { window.addEventListener("app-ready", fn, { once: true }); }
}

/* ═══════════════════════════════════════════════════════════════════════════
   Expedition list (left panel)
   ═════════════════════════════════════════════════════════════════════════ */

async function loadExpediciones() {
  try {
    const r  = await fetch(`${API}/api/expedientes`);
    expediciones = await r.json();
    renderExpedicionList();
  } catch {
    toast("Error al cargar expedientes", "error");
  }
}

function renderExpedicionList() {
  const listEl   = document.getElementById("expedition-list");
  const emptyEl  = document.getElementById("expedition-list-empty");
  const search   = (document.getElementById("search-expedientes").value || "").toLowerCase();

  const filtered = expediciones.filter(e => e.nombre.toLowerCase().includes(search));

  if (!filtered.length) {
    listEl.innerHTML = "";
    emptyEl.style.display = "";
    return;
  }
  emptyEl.style.display = "none";

  listEl.innerHTML = filtered.map(e => `
    <li class="exp-item${e.nombre === selectedNombre ? " active" : ""}"
        data-nombre="${esc(e.nombre)}" tabindex="0">
      <div class="exp-item-info">
        <span class="exp-item-name" title="${esc(e.nombre)}">${esc(e.nombre)}</span>
        <span class="exp-item-count">${e.archivos} archivo${e.archivos !== 1 ? "s" : ""}</span>
      </div>
      <span class="exp-item-dot"></span>
    </li>
  `).join("");

  listEl.querySelectorAll(".exp-item").forEach(item => {
    item.addEventListener("click", () => selectExpedicion(item.dataset.nombre));
    item.addEventListener("contextmenu", (e) => openContextMenu(e, item.dataset.nombre));
    item.addEventListener("keydown", (e) => {
      if (e.key === "Enter") selectExpedicion(item.dataset.nombre);
    });
  });
}

async function selectExpedicion(nombre) {
  selectedNombre = nombre;
  localStorage.setItem("last_expedicion", nombre);
  renderExpedicionList();
  document.getElementById("empty-state").style.display   = "none";
  document.getElementById("expedition-content").style.display = "flex";
  document.getElementById("expedition-title").textContent = nombre;
  document.getElementById("cfg-output-name").value = nombre;

  resetGenerationUI();
  archivos = [];
  renderFilesTable();
  document.getElementById("expedition-stats").textContent = "Cargando…";

  try {
    const r = await fetch(`${API}/api/expedientes/${enc(nombre)}/archivos`);
    if (!r.ok) throw new Error();
    const data = await r.json();
    archivos = data.archivos || [];
    loadFolioConfig(data.config_folio || {});
    renderFilesTable();
    updateStats();
  } catch {
    toast("Error al cargar archivos del expediente", "error");
  }
}

function updateStats() {
  const total = archivos.filter(f => f.paginas > 0).reduce((s, f) => s + f.paginas, 0);
  document.getElementById("expedition-stats").textContent =
    `${archivos.length} archivo${archivos.length !== 1 ? "s" : ""} · ${total.toLocaleString("es")} páginas en total`;
  updateGenerateBtn();
}

/* ── Folio config loading ────────────────────────────────────────────────── */
function loadFolioConfig(cfg) {
  if (cfg.activo          !== undefined) document.getElementById("cfg-foliar").checked    = cfg.activo;
  if (cfg.posicion)                      document.getElementById("cfg-position").value    = cfg.posicion;
  if (cfg.tamano          !== undefined) document.getElementById("cfg-fontsize").value    = cfg.tamano;
  if (cfg.margen_superior !== undefined) document.getElementById("cfg-margin-top").value  = cfg.margen_superior;
  if (cfg.margen_lateral  !== undefined) document.getElementById("cfg-margin-right").value= cfg.margen_lateral;
  if (cfg.iniciar_desde   !== undefined) document.getElementById("cfg-folio-start").value = cfg.iniciar_desde;
  updateFolioOptionsVisibility();
}

function getFolioConfig() {
  return {
    activo:          document.getElementById("cfg-foliar").checked,
    posicion:        document.getElementById("cfg-position").value,
    tamano:          parseFloat(document.getElementById("cfg-fontsize").value)    || 11,
    margen_superior: parseFloat(document.getElementById("cfg-margin-top").value)  || 20,
    margen_lateral:  parseFloat(document.getElementById("cfg-margin-right").value)|| 30,
    iniciar_desde:   Math.max(1, parseInt(document.getElementById("cfg-folio-start").value) || 1),
  };
}

async function saveFolioConfig() {
  if (!selectedNombre) return;
  try {
    await fetch(`${API}/api/expedientes/${enc(selectedNombre)}/config`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ config_folio: getFolioConfig() }),
    });
  } catch { /* silent */ }
}

/* ═══════════════════════════════════════════════════════════════════════════
   Files table (right panel)
   ═════════════════════════════════════════════════════════════════════════ */

function renderFilesTable() {
  const emptyEl  = document.getElementById("files-empty");
  const tableEl  = document.getElementById("files-table");
  const tbodyEl  = document.getElementById("files-tbody");

  if (!archivos.length) {
    emptyEl.style.display  = "";
    tableEl.style.display  = "none";
    return;
  }
  emptyEl.style.display  = "none";
  tableEl.style.display  = "";

  tbodyEl.innerHTML = archivos.map((f, i) => {
    const pagesHtml = f.uploading
      ? `<span class="spinner-sm"></span>`
      : f.paginas > 0
        ? `<span class="pages-badge">${f.paginas} págs.</span>`
        : `<span class="pages-err" title="${esc(f.error || '')}">⚠ error</span>`;

    return `
      <tr class="file-row" draggable="true" data-nombre="${esc(f.nombre)}">
        <td class="col-handle handle-cell">${ICO_GRIP}</td>
        <td class="col-num">${i + 1}</td>
        <td class="col-icon">${fileIcon(f.nombre)}</td>
        <td class="col-name"><span class="file-name-text" title="${esc(f.nombre)}">${esc(f.nombre)}</span></td>
        <td class="col-pages">${pagesHtml}</td>
        <td class="col-actions">
          ${f.uploading ? "" : `<button class="btn-remove-file" title="Eliminar" data-nombre="${esc(f.nombre)}">✕</button>`}
        </td>
      </tr>
    `;
  }).join("");

  initFileDragSort();

  tbodyEl.querySelectorAll(".btn-remove-file").forEach(btn => {
    btn.addEventListener("click", () => removeArchivo(btn.dataset.nombre));
  });
}

/* ── Drag-sort rows ──────────────────────────────────────────────────────── */
function initFileDragSort() {
  const tbody = document.getElementById("files-tbody");
  let dragged = null;

  tbody.querySelectorAll(".file-row").forEach(row => {
    row.addEventListener("dragstart", e => {
      dragged = row;
      row.classList.add("dragging");
      e.dataTransfer.effectAllowed = "move";
    });
    row.addEventListener("dragend", () => {
      row.classList.remove("dragging");
      tbody.querySelectorAll(".file-row").forEach(r => r.classList.remove("drag-over-top", "drag-over-bottom"));
      const nuevoOrden = [...tbody.querySelectorAll(".file-row")].map(r => r.dataset.nombre);
      archivos = nuevoOrden.map(n => archivos.find(f => f.nombre === n)).filter(Boolean);
      renderFilesTable();
      saveOrden(nuevoOrden);
    });
    row.addEventListener("dragover", e => {
      e.preventDefault();
      if (!dragged || dragged === row) return;
      row.classList.remove("drag-over-top", "drag-over-bottom");
      const mid = row.getBoundingClientRect().top + row.offsetHeight / 2;
      row.classList.add(e.clientY < mid ? "drag-over-top" : "drag-over-bottom");
    });
    row.addEventListener("dragleave", () => {
      row.classList.remove("drag-over-top", "drag-over-bottom");
    });
    row.addEventListener("drop", e => {
      e.preventDefault();
      if (!dragged || dragged === row) return;
      row.classList.remove("drag-over-top", "drag-over-bottom");
      const mid = row.getBoundingClientRect().top + row.offsetHeight / 2;
      if (e.clientY < mid) tbody.insertBefore(dragged, row);
      else tbody.insertBefore(dragged, row.nextSibling);
    });
  });
}

async function saveOrden(orden) {
  if (!selectedNombre) return;
  try {
    await fetch(`${API}/api/expedientes/${enc(selectedNombre)}/orden`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ orden }),
    });
  } catch { /* silent */ }
}

/* ═══════════════════════════════════════════════════════════════════════════
   Adding files
   ═════════════════════════════════════════════════════════════════════════ */

document.getElementById("btn-add-files").addEventListener("click", () => {
  document.getElementById("file-input").click();
});

document.getElementById("file-input").addEventListener("change", (e) => {
  handleFileObjects([...e.target.files]);
  e.target.value = "";
});

/* Drag-drop onto files-drop-area */
const dropArea = document.getElementById("files-drop-area");
dropArea.addEventListener("dragover", e => { e.preventDefault(); dropArea.classList.add("drag-over"); });
dropArea.addEventListener("dragleave", () => dropArea.classList.remove("drag-over"));
dropArea.addEventListener("drop", e => {
  e.preventDefault();
  dropArea.classList.remove("drag-over");
  handleFileObjects([...e.dataTransfer.files]);
});

async function handleFileObjects(fileArray) {
  if (!selectedNombre) { toast("Selecciona un expediente primero", "warn"); return; }

  const supported = fileArray.filter(f => {
    const ext = (f.name.split(".").pop() || "").toLowerCase();
    return _ALL_EXT.has(ext);
  });
  const skipped = fileArray.length - supported.length;
  if (skipped > 0) toast(`${skipped} archivo(s) ignorados (tipo no compatible)`, "warn");
  if (!supported.length) return;

  for (const file of supported) {
    await uploadArchivoToExpedicion(file);
  }
  updateStats();
}

async function uploadArchivoToExpedicion(file, replace = false) {
  const nombre = selectedNombre;

  // Optimistic: add uploading placeholder
  const placeholder = { nombre: file.name, paginas: 0, tamanio: file.size, uploading: true };
  archivos.push(placeholder);
  renderFilesTable();

  const form = new FormData();
  form.append("file", file);

  try {
    const url = `${API}/api/expedientes/${enc(nombre)}/archivos${replace ? "?replace=true" : ""}`;
    const r   = await fetch(url, { method: "POST", body: form });

    // Remove placeholder
    archivos = archivos.filter(f => !(f.uploading && f.nombre === file.name));

    if (r.status === 409 && !replace) {
      const d = await r.json().catch(() => ({}));
      if (confirm(`${d.detail || "Ya existe ese archivo"}. ¿Reemplazar?`)) {
        await uploadArchivoToExpedicion(file, true);
        return;
      }
      renderFilesTable();
      return;
    }

    if (!r.ok) {
      const d = await r.json().catch(() => ({}));
      toast(`Error subiendo "${file.name}": ${d.detail || r.statusText}`, "error", 5000);
      renderFilesTable();
      return;
    }

    const data = await r.json();
    archivos.push({ nombre: data.nombre, paginas: data.paginas, tamanio: data.tamanio });

    // Reload expedition list count
    loadExpediciones();
    renderFilesTable();
    toast(`"${data.nombre}" agregado (${data.paginas} págs.)`, "success", 3000);

  } catch (err) {
    archivos = archivos.filter(f => !(f.uploading && f.nombre === file.name));
    renderFilesTable();
    toast(`Error subiendo "${file.name}": ${err.message}`, "error", 5000);
  }
}

async function removeArchivo(filename) {
  if (!selectedNombre) return;
  if (!confirm(`¿Eliminar "${filename}" del expediente? El archivo se borrará del disco.`)) return;

  try {
    const r = await fetch(`${API}/api/expedientes/${enc(selectedNombre)}/archivos/${enc(filename)}`, {
      method: "DELETE",
    });
    if (!r.ok) throw new Error();
    archivos = archivos.filter(f => f.nombre !== filename);
    renderFilesTable();
    updateStats();
    loadExpediciones();
    toast(`"${filename}" eliminado`, "success", 2500);
  } catch {
    toast("Error al eliminar el archivo", "error");
  }
}

/* ═══════════════════════════════════════════════════════════════════════════
   Expedition CRUD
   ═════════════════════════════════════════════════════════════════════════ */

/* New expedition */
document.getElementById("btn-new-expediente").addEventListener("click", openNewExpeditionModal);

function openNewExpeditionModal() {
  document.getElementById("new-exp-name").value   = "";
  document.getElementById("new-exp-error").style.display = "none";
  document.getElementById("modal-new-expedition").style.display = "flex";
  setTimeout(() => document.getElementById("new-exp-name").focus(), 50);
}

function closeNewExpeditionModal() {
  document.getElementById("modal-new-expedition").style.display = "none";
}

document.getElementById("btn-close-new-exp").addEventListener("click", closeNewExpeditionModal);
document.getElementById("btn-cancel-new-exp").addEventListener("click", closeNewExpeditionModal);
document.getElementById("modal-new-expedition").addEventListener("click", e => {
  if (e.target === document.getElementById("modal-new-expedition")) closeNewExpeditionModal();
});
document.getElementById("new-exp-name").addEventListener("keydown", e => {
  if (e.key === "Enter") confirmCreateExpedition();
});

document.getElementById("btn-confirm-new-exp").addEventListener("click", confirmCreateExpedition);

async function confirmCreateExpedition() {
  const nombre = document.getElementById("new-exp-name").value.trim();
  const errEl  = document.getElementById("new-exp-error");
  if (!nombre) { errEl.textContent = "El nombre es obligatorio."; errEl.style.display = ""; return; }
  errEl.style.display = "none";

  const btn = document.getElementById("btn-confirm-new-exp");
  btn.disabled = true;
  try {
    const r = await fetch(`${API}/api/expedientes`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ nombre }),
    });
    if (r.status === 409) { errEl.textContent = "Ya existe un expediente con ese nombre."; errEl.style.display = ""; return; }
    if (!r.ok) { const d = await r.json().catch(() => ({})); errEl.textContent = d.detail || "Error al crear."; errEl.style.display = ""; return; }
    closeNewExpeditionModal();
    await loadExpediciones();
    selectExpedicion(nombre);
    toast(`Expediente "${nombre}" creado`, "success");
  } catch {
    errEl.textContent = "Error de conexión.";
    errEl.style.display = "";
  } finally {
    btn.disabled = false;
  }
}

/* Rename */
let renamingNombre = null;

function openRenameModal(nombre) {
  renamingNombre = nombre;
  document.getElementById("rename-exp-name").value = nombre;
  document.getElementById("rename-exp-error").style.display = "none";
  document.getElementById("modal-rename-expedition").style.display = "flex";
  setTimeout(() => {
    const inp = document.getElementById("rename-exp-name");
    inp.focus();
    inp.select();
  }, 50);
}

function closeRenameModal() {
  document.getElementById("modal-rename-expedition").style.display = "none";
  renamingNombre = null;
}

document.getElementById("btn-close-rename").addEventListener("click", closeRenameModal);
document.getElementById("btn-cancel-rename").addEventListener("click", closeRenameModal);
document.getElementById("modal-rename-expedition").addEventListener("click", e => {
  if (e.target === document.getElementById("modal-rename-expedition")) closeRenameModal();
});
document.getElementById("rename-exp-name").addEventListener("keydown", e => {
  if (e.key === "Enter") confirmRename();
});
document.getElementById("btn-confirm-rename").addEventListener("click", confirmRename);

async function confirmRename() {
  const nuevoNombre = document.getElementById("rename-exp-name").value.trim();
  const errEl       = document.getElementById("rename-exp-error");
  if (!nuevoNombre) { errEl.textContent = "El nombre es obligatorio."; errEl.style.display = ""; return; }
  errEl.style.display = "none";

  const btn = document.getElementById("btn-confirm-rename");
  btn.disabled = true;
  try {
    const r = await fetch(`${API}/api/expedientes/${enc(renamingNombre)}/rename`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ nombre_nuevo: nuevoNombre }),
    });
    if (r.status === 409) { errEl.textContent = "Ya existe un expediente con ese nombre."; errEl.style.display = ""; return; }
    if (!r.ok) { const d = await r.json().catch(() => ({})); errEl.textContent = d.detail || "Error."; errEl.style.display = ""; return; }
    const wasSelected = (renamingNombre === selectedNombre);
    closeRenameModal();
    await loadExpediciones();
    if (wasSelected) selectExpedicion(nuevoNombre);
    toast(`Renombrado a "${nuevoNombre}"`, "success");
  } catch {
    errEl.textContent = "Error de conexión.";
    errEl.style.display = "";
  } finally {
    btn.disabled = false;
  }
}

/* Delete */
async function deleteExpedicion(nombre) {
  if (!confirm(`¿Eliminar el expediente "${nombre}" y todos sus archivos? Esta acción no se puede deshacer.`)) return;
  try {
    const r = await fetch(`${API}/api/expedientes/${enc(nombre)}`, { method: "DELETE" });
    if (!r.ok) throw new Error();
    if (selectedNombre === nombre) {
      selectedNombre = null;
      archivos = [];
      document.getElementById("expedition-content").style.display = "none";
      document.getElementById("empty-state").style.display = "";
    }
    await loadExpediciones();
    toast(`Expediente "${nombre}" eliminado`, "success");
  } catch {
    toast("Error al eliminar el expediente", "error");
  }
}

/* ── Search ──────────────────────────────────────────────────────────────── */
document.getElementById("search-expedientes").addEventListener("input", renderExpedicionList);

/* ═══════════════════════════════════════════════════════════════════════════
   Context menu
   ═════════════════════════════════════════════════════════════════════════ */
const ctxMenu = document.getElementById("context-menu");

function openContextMenu(e, nombre) {
  e.preventDefault();
  ctxNombre = nombre;
  ctxMenu.style.display = "";
  const x = Math.min(e.clientX, window.innerWidth  - ctxMenu.offsetWidth  - 8);
  const y = Math.min(e.clientY, window.innerHeight - ctxMenu.offsetHeight - 8);
  ctxMenu.style.left = x + "px";
  ctxMenu.style.top  = y + "px";
}

function closeContextMenu() {
  ctxMenu.style.display = "none";
  ctxNombre = null;
}

document.addEventListener("click",       closeContextMenu);
document.addEventListener("contextmenu", e => { if (!e.target.closest(".exp-item")) closeContextMenu(); });

document.getElementById("ctx-rename").addEventListener("click", () => {
  if (ctxNombre) openRenameModal(ctxNombre);
  closeContextMenu();
});
document.getElementById("ctx-delete").addEventListener("click", () => {
  if (ctxNombre) deleteExpedicion(ctxNombre);
  closeContextMenu();
});

/* ═══════════════════════════════════════════════════════════════════════════
   Folio config changes → auto-save
   ═════════════════════════════════════════════════════════════════════════ */
let _folioSaveTimer = null;

function scheduleFolioSave() {
  clearTimeout(_folioSaveTimer);
  _folioSaveTimer = setTimeout(saveFolioConfig, 800);
  updateFolioOptionsVisibility();
}

function updateFolioOptionsVisibility() {
  const on = document.getElementById("cfg-foliar").checked;
  document.getElementById("foliar-options").style.display = on ? "" : "none";
}

["cfg-foliar","cfg-position","cfg-fontsize","cfg-margin-top","cfg-margin-right","cfg-folio-start"].forEach(id => {
  const el = document.getElementById(id);
  if (el) {
    el.addEventListener("change", scheduleFolioSave);
    el.addEventListener("input",  scheduleFolioSave);
  }
});
updateFolioOptionsVisibility();

/* ═══════════════════════════════════════════════════════════════════════════
   Generation
   ═════════════════════════════════════════════════════════════════════════ */

function updateGenerateBtn() {
  const hasFiles  = archivos.filter(f => !f.uploading && f.paginas > 0).length > 0;
  const btn       = document.getElementById("btn-generate");
  const btnText   = document.getElementById("btn-generate-text");
  btn.disabled    = !hasFiles;
  btnText.textContent = hasFiles ? "⚡ Generar expediente" : "Agrega archivos para continuar";
}

document.getElementById("btn-generate").addEventListener("click", generate);

async function generate() {
  if (!selectedNombre) return;
  if (archivos.filter(f => !f.uploading && f.paginas > 0).length === 0) return;

  const outputName = document.getElementById("cfg-output-name").value.trim();
  const errEl      = document.getElementById("nombre-error");
  if (!outputName) {
    errEl.style.display = "";
    document.getElementById("cfg-output-name").focus();
    return;
  }
  errEl.style.display = "none";

  document.getElementById("btn-generate").disabled = true;
  document.getElementById("btn-generate-text").innerHTML = `<span class="spinner"></span> Procesando…`;
  resetGenerationProgress();
  document.getElementById("result-section").style.display = "none";
  document.getElementById("progress-section").style.display = "";

  try {
    const r = await fetch(`${API}/api/expedientes/${enc(selectedNombre)}/generar`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        output_name: outputName,
        config_folio: getFolioConfig(),
      }),
    });
    if (!r.ok) {
      const d = await r.json().catch(() => ({}));
      throw new Error(d.detail || "Error al iniciar generación");
    }
    const { task_id } = await r.json();
    activeTaskId = task_id;
    startPolling(task_id);
  } catch (err) {
    resetGenerationUI();
    toast(`Error: ${err.message}`, "error", 6000);
  }
}

/* ── Polling ──────────────────────────────────────────────────────────────── */
function startPolling(taskId) {
  if (pollTimer) clearInterval(pollTimer);
  pollTimer = setInterval(() => pollTask(taskId), POLL_MS);
}

async function pollTask(taskId) {
  try {
    const r    = await fetch(`${API}/api/task/${taskId}`);
    if (!r.ok) return;
    const task = await r.json();

    document.getElementById("progress-fill").style.width = `${task.progress}%`;
    document.getElementById("progress-msg").textContent  = task.message || "";
    document.getElementById("progress-pct").style.display = "none";

    if (task.status === "done") {
      stopPolling();
      resetGenerationBtn();
      document.getElementById("progress-section").style.display = "none";
      showResult(task);
    } else if (task.status === "error") {
      stopPolling();
      resetGenerationBtn();
      document.getElementById("progress-section").style.display = "none";
      toast(`Error: ${task.error || task.message}`, "error", 8000);
    } else if (task.status === "cancelled") {
      stopPolling();
      resetGenerationBtn();
      document.getElementById("progress-section").style.display = "none";
      toast("Generación cancelada", "warn", 3000);
    }
  } catch { /* network hiccup */ }
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
  resetGenerationBtn();
  document.getElementById("progress-section").style.display = "none";
}

document.getElementById("btn-cancel-gen").addEventListener("click", cancelGeneration);

/* ── Result ───────────────────────────────────────────────────────────────── */
function showResult(task) {
  const fname = task.result_file;
  document.getElementById("result-name").textContent = fname;
  const secs = task.elapsed_seconds != null ? ` · ${task.elapsed_seconds}s` : "";
  document.getElementById("result-meta").textContent =
    `${task.total_pages} páginas foliadas${secs}`;

  const dlBtn = document.getElementById("btn-download");
  dlBtn.href     = `${API}/api/download/${enc(fname)}`;
  dlBtn.download = fname;

  const failedWarn = document.getElementById("failed-warn");
  const failedList = document.getElementById("failed-list");
  if (task.failed_files && task.failed_files.length) {
    failedWarn.style.display = "";
    failedList.innerHTML = task.failed_files.map(f => `<li>${esc(f)}</li>`).join("");
  } else {
    failedWarn.style.display = "none";
  }

  document.getElementById("result-section").style.display = "";

  if (task.sin_registro) {
    toast("Expediente generado sin registrar (límite diario de mismo nombre)", "warn", 8000);
  } else {
    toast(`¡Listo! ${task.total_pages} páginas`, "success", 5000);
  }

  if (task.total_mes !== undefined && task.total_mes !== null) {
    window.dispatchEvent(new CustomEvent("expediente-registrado", { detail: { total_mes: task.total_mes } }));
  }
}

/* ── Reset helpers ────────────────────────────────────────────────────────── */
function resetGenerationBtn() {
  const hasFiles = archivos.filter(f => !f.uploading && f.paginas > 0).length > 0;
  const btn      = document.getElementById("btn-generate");
  const btnText  = document.getElementById("btn-generate-text");
  btn.disabled   = !hasFiles;
  btnText.textContent = hasFiles ? "⚡ Generar expediente" : "Agrega archivos para continuar";
}

function resetGenerationProgress() {
  document.getElementById("progress-fill").style.width = "0";
  document.getElementById("progress-msg").textContent  = "Iniciando…";
  document.getElementById("btn-cancel-gen").disabled   = false;
}

function resetGenerationUI() {
  resetGenerationBtn();
  document.getElementById("progress-section").style.display = "none";
  document.getElementById("result-section").style.display   = "none";
}

/* ── Output name error clear ─────────────────────────────────────────────── */
document.getElementById("cfg-output-name").addEventListener("input", () => {
  document.getElementById("nombre-error").style.display = "none";
});

/* ═══════════════════════════════════════════════════════════════════════════
   Settings modal
   ═════════════════════════════════════════════════════════════════════════ */
document.getElementById("btn-settings").addEventListener("click", openSettingsModal);

async function openSettingsModal() {
  document.getElementById("modal-settings").style.display = "flex";
  try {
    const r = await fetch(`${API}/api/config`);
    const d = await r.json();
    document.getElementById("settings-folder").value = d.carpeta_raiz || "";
    document.getElementById("settings-folder-hint").textContent =
      d.carpeta_raiz ? `Carpeta actual: ${d.carpeta_raiz}` : "No configurada";
  } catch {}
}

function closeSettingsModal() {
  document.getElementById("modal-settings").style.display = "none";
}

document.getElementById("btn-close-settings").addEventListener("click", closeSettingsModal);
document.getElementById("btn-cancel-settings").addEventListener("click", closeSettingsModal);
document.getElementById("modal-settings").addEventListener("click", e => {
  if (e.target === document.getElementById("modal-settings")) closeSettingsModal();
});

document.getElementById("btn-settings-browse").addEventListener("click", () => {
  document.getElementById("settings-folder-input").click();
});
document.getElementById("settings-folder-input").addEventListener("change", e => {
  const files = e.target.files;
  if (files && files.length > 0) {
    const path = files[0].webkitRelativePath.split("/")[0];
    document.getElementById("settings-folder").value = path;
  }
});

document.getElementById("btn-save-settings").addEventListener("click", async () => {
  const path = document.getElementById("settings-folder").value.trim();
  if (!path) { toast("Escribe una ruta válida", "warn"); return; }
  const btn = document.getElementById("btn-save-settings");
  btn.disabled = true;
  try {
    const r = await fetch(`${API}/api/config`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ carpeta_raiz: path }),
    });
    if (!r.ok) { const d = await r.json().catch(() => ({})); toast(d.detail || "Error al guardar", "error"); return; }
    closeSettingsModal();
    toast("Configuración guardada", "success");
    selectedNombre = null;
    archivos = [];
    document.getElementById("expedition-content").style.display = "none";
    document.getElementById("empty-state").style.display = "";
    loadExpediciones();
  } catch {
    toast("Error de conexión", "error");
  } finally {
    btn.disabled = false;
  }
});

/* ═══════════════════════════════════════════════════════════════════════════
   Init on app-ready
   ═════════════════════════════════════════════════════════════════════════ */
whenReady(() => {
  loadExpediciones();

  // Restore last selected expedition from localStorage
  const last = localStorage.getItem("last_expedicion");
  if (last) {
    setTimeout(() => {
      const found = expediciones.find(e => e.nombre === last);
      if (found) selectExpedicion(last);
    }, 400);
  }
});

