# Funciones clave — Expediente Digital

## `pdf_processor.py`

### `analyze_pdf_file(file_path: str) → tuple[int, str | None]`

Analiza un PDF para obtener su cantidad de páginas.

**Retorna:** `(page_count, error_msg)`
- `page_count = -1` si el archivo no es usable (vacío, encriptado, dañado)
- `error_msg = None` si todo está bien

**Qué revisa:**
1. Tamaño del archivo > 0 bytes
2. Si está encriptado, intenta autenticación con contraseña vacía (PDFs sin contraseña real pero marcados como encriptados)
3. Que tenga al menos 1 página legible

---

### `convert_image_to_pdf(src_path: str, dst_path: str) → None`

Convierte una imagen (JPG, PNG, GIF, BMP, TIFF, WEBP) a PDF de una página tamaño Oficio (612×935 pt).

**Proceso:**
1. Abre la imagen con Pillow, convierte a RGB si hace falta
2. Calcula el ratio de escala para que quepa en el área útil (Oficio menos 40px de margen cada lado)
3. Centra la imagen en la página
4. Guarda con `garbage=3, deflate=True` (máxima compresión)

---

### `convert_docx_to_pdf(src_path: str, dst_path: str) → bool`

Convierte un archivo Word (.docx) a PDF usando python-docx + ReportLab (sin LibreOffice).

**Limitación importante:** Solo extrae texto plano. Tablas, imágenes embebidas, encabezados complejos y estilos avanzados se pierden. Si el .docx tiene contenido importante no textual, el resultado puede ser incompleto.

**Retorna:** `True` si tuvo éxito, `False` si falló (sin excepción — el caller maneja el fallback).

---

### `merge_and_foliate(file_paths, output_path, config, progress_cb) → dict`

Función principal de procesamiento. Fusiona PDFs y estampa el número de folio en cada página.

**Parámetros:**
- `file_paths: list[str]` — rutas de PDFs en orden de fusión
- `output_path: str` — dónde guardar el PDF resultante
- `config: dict` — configuración de foliación (ver abajo)
- `progress_cb: Callable[[str, float], None]` — callback de progreso `(mensaje, porcentaje)`

**Claves de `config`:**
| Clave | Tipo | Default | Descripción |
|---|---|---|---|
| `foliar` | bool | `True` | Si `False`, fusiona sin numerar |
| `folio_start` | int | `1` | Número del primer folio |
| `font_size` | float | `11` | Tamaño de fuente del folio en puntos |
| `margin_top` | float | `20` | Margen superior en puntos |
| `margin_right` | float | `30` | Margen derecho en puntos |
| `position` | str | `"top-right"` | Posición: `top-right`, `top-left`, `bottom-right`, `bottom-left` |

**Retorna:** `{"total_pages": int, "failed_files": list[str]}`

**Lanza:** `ValueError` si no se pudo procesar ningún archivo.

**Fases de ejecución:**
```
Phase 1 (0–48%):   Fusión — insert_pdf() por cada archivo
Phase 1.5 (49%):   Normalización de rotaciones — bakes /Rotate into content stream
Phase 2 (48–94%):  Foliación — _stamp_folio() por cada página (si config.foliar)
Phase 3 (95–100%): Guardado — fitz.save(garbage=2, deflate=True, clean=False)
```

---

### `_normalize_rotation(doc, page_idx) → None`

Normaliza la rotación de una página PDF baking el `/Rotate` en el content stream, dejando `rotation = 0`. Necesario porque al fusionar PDFs con distintas orientaciones, el folio se estampa sobre el tamaño "raw" sin rotar, y quedaría en posición incorrecta.

- **Primary path:** usa `page.remove_rotation()` (PyMuPDF ≥ 1.22)
- **Fallback:** reescribe el content stream manualmente con matrices CTM para rotaciones 90°, 180°, 270°

---

### `_stamp_folio(page, number, font_size, margin_top, margin_right, position) → None`

Inserta el número de folio en la página. Usa las dimensiones reales de la página (no asume tamaño estándar).

Primero intenta `insert_textbox()` (que ajusta texto al recuadro). Si el retorno es negativo (texto no cabe), cae back a `insert_text()` como segunda opción.

---

## `backend/main.py`

### `_get_hardware_id() → str`

Genera un identificador único y estable para la máquina.

```python
mac = ':'.join(['{:02x}'.format((uuid.getnode() >> e) & 0xff) for e in range(0,48,8)][::-1])
raw = f"{mac}-{platform.processor()}-{platform.system()}{platform.version()}"
return hashlib.sha256(raw.encode()).hexdigest()[:32]
```

**Componentes:** dirección MAC + procesador + nombre y versión del SO.
**Salida:** hex de 32 caracteres (SHA-256 truncado).

**Nota:** Cambia si se reemplaza la tarjeta de red o se instala el SO en otro hardware. Inmune a cambios de usuario, nombre de máquina y configuraciones de red menores.

---

### `_registrar_expediente(output_path, nombre_expediente, paginas_procesadas, tiempo_generacion) → tuple[bool, int]`

Registra el expediente en el servidor de licencias antes de entregarlo al usuario. Si falla, el expediente NO se entrega (el backend retorna error al frontend).

**Parámetros:**
- `output_path: str` — ruta local del PDF generado (para calcular el hash)
- `nombre_expediente: str` — nombre del expediente (viene del usuario)
- `paginas_procesadas: int` — total de páginas del PDF resultante
- `tiempo_generacion: float` — segundos que tardó el procesamiento

**Qué hace:**
1. Lee el PDF y calcula `SHA256(contenido + timestamp)` como hash único anti-duplicados
2. `POST /api/expediente/registrar` con el payload completo
3. Retorna `(True, total_mes)` si el servidor responde `ok: true`
4. Retorna `(False, 0)` ante cualquier error de red o respuesta negativa

**Cuándo se llama:** en `_run_task()` después de que `merge_and_foliate()` termina exitosamente, pero solo si el nombre del expediente no excede el throttle diario (máx 2 veces el mismo nombre por día).

---

### `_check_and_register_nombre(nombre: str) → tuple[int, bool]`

Throttling local anti-abuso para evitar que se registren más de 2 expedientes con el mismo nombre en el mismo día.

**Almacenamiento:** archivo JSON en `%LOCALAPPDATA%\ExpedienteDigital\nombres_usados.json`, con estructura:
```json
{ "fecha": "2026-08-03", "nombres": { "EXPEDIENTE LEIDY JOHANA": 1 } }
```

**Retorna:** `(count_antes, registrado)`
- Si `count_antes < 2`: incrementa contador, retorna `(n, True)` → el expediente se registra en el servidor
- Si `count_antes >= 2`: retorna `(n, False)` → el expediente se genera localmente pero NO se registra (no se cobra)

---

### `_run_task(task_id, file_paths, output_path, output_name, config, session_ids, file_ids, nombre_expediente) → None`

Función que corre en el ThreadPoolExecutor (hilo separado). Orquesta el flujo completo de generación.

**Flujo:**
```
1. merge_and_foliate(file_paths, output_path, config, cb)
   ← result = { total_pages, failed_files }

2. _check_and_register_nombre(nombre_expediente)
   ← (count_antes, puede_registrar)

3a. Si puede_registrar:
    _registrar_expediente(output_path, nombre, result["total_pages"], elapsed)
    ← (ok, total_mes)
    Si NOT ok: task["status"] = "error", return (expediente no entregado)

3b. Si NOT puede_registrar:
    Genera localmente sin registrar. No se cobra, no se cuenta.

4. task["status"] = "done"
   task["result_file"] = output_name
   task["total_pages"] = result["total_pages"]

5. (finally) Limpieza de archivos temporales de la sesión
```

**Callback de progreso `cb(msg, pct)`:** actualiza `task["message"]` y `task["progress"]`. Si el task tiene `"cancelled": True`, lanza `InterruptedError` para abortar el procesamiento.

---

### Endpoints FastAPI completos

| Método | Ruta | Descripción |
|---|---|---|
| GET | `/` | Sirve el frontend (index.html) |
| POST | `/api/session` | Crea sesión temporal de upload |
| DELETE | `/api/session/{id}` | Elimina sesión y sus archivos |
| POST | `/api/upload` | Sube PDF/imagen/Word, convierte si hace falta |
| POST | `/api/count-pages` | Devuelve conteo de páginas por file_id (en memoria) |
| POST | `/api/load-folder` | Carga archivos desde carpeta del sistema de archivos |
| POST | `/api/process` | Lanza tarea de fusión+foliación en segundo plano |
| GET | `/api/task/{id}` | Estado de tarea (status, progress, message, result_file) |
| DELETE | `/api/task/{id}` | Cancela tarea en curso |
| GET | `/api/download/{filename}` | Descarga el PDF generado |
| DELETE | `/api/files/{file_id}` | Elimina un archivo subido de la sesión |
| POST | `/api/cleanup` | Limpia sesiones y archivos temporales obsoletos |
| GET | `/api/update/check` | Consulta si hay versión nueva disponible |
| GET | `/api/version` | Devuelve la versión instalada (lee version.txt) |
| GET | `/api/health` | Healthcheck (status, uploaded_files, active_tasks) |
| GET | `/api/browse-folder` | Abre diálogo nativo de Windows para elegir carpeta |
| GET | `/api/config` | Lee config.json (carpeta_raíz, preferencias) |
| POST | `/api/config` | Guarda config.json |
| GET | `/api/expedientes` | Lista expedientes en la carpeta raíz configurada |
| POST | `/api/expedientes` | Crea nuevo expediente (carpeta + expediente.json) |
| PUT | `/api/expedientes/{nombre}/rename` | Renombra un expediente |
| DELETE | `/api/expedientes/{nombre}` | Elimina un expediente y sus archivos |
| GET | `/api/expedientes/{nombre}/archivos` | Lista archivos del expediente con conteo de páginas |
| POST | `/api/expedientes/{nombre}/archivos` | Agrega archivos a un expediente |
| DELETE | `/api/expedientes/{nombre}/archivos/{filename}` | Elimina archivo del expediente |
| PUT | `/api/expedientes/{nombre}/orden` | Actualiza el orden de archivos |
| PUT | `/api/expedientes/{nombre}/config` | Actualiza config de folio del expediente |
| POST | `/api/expedientes/{nombre}/generar` | Genera el PDF del expediente (lanza tarea) |
| GET | `/api/licencia` | Verifica licencia activa consultando al servidor Railway |

---

## Flujo de generación end-to-end

```
Usuario (browser)                    FastAPI                        Servidor Railway
      │                                 │                                  │
      │  POST /api/session              │                                  │
      │────────────────────────────────►│ sessions.create()                │
      │◄────────────────────────────────│ { session_id }                   │
      │                                 │                                  │
      │  POST /api/upload (archivos)    │                                  │
      │────────────────────────────────►│ convert si imagen/docx           │
      │◄────────────────────────────────│ { file_id, pages, error }        │
      │  (repetir por cada archivo)     │                                  │
      │                                 │                                  │
      │  POST /api/process              │                                  │
      │  { file_ids, config, nombre }   │                                  │
      │────────────────────────────────►│ ThreadPoolExecutor.submit(       │
      │◄────────────────────────────────│   _run_task(...))                │
      │  { task_id }                    │                                  │
      │                                 │                                  │
      │  GET /api/task/{id} (polling)   │                                  │
      │────────────────────────────────►│ return tasks[task_id]            │
      │◄────────────────────────────────│ { status, progress, message }    │
      │  (repetir hasta status=done)    │                                  │
      │                                 │   merge_and_foliate()            │
      │                                 │   _registrar_expediente()        │
      │                                 │────────────────────────────────►│
      │                                 │                                  │ INSERT expediente
      │                                 │◄────────────────────────────────│ { ok, total_mes }
      │                                 │                                  │
      │  GET /api/download/{filename}   │                                  │
      │────────────────────────────────►│ FileResponse(pdf)                │
      │◄────────────────────────────────│ [PDF]                            │
```
