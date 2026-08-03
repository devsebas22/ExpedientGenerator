# Arquitectura — Expediente Digital (App Desktop)

## Stack tecnológico

| Capa | Tecnología | Versión |
|---|---|---|
| API backend | FastAPI + Uvicorn | 0.115.6 / 0.34.0 |
| Procesamiento PDF | PyMuPDF (fitz) | 1.25.5 |
| Conversión imágenes | Pillow | ≥ 10.0 |
| Conversión Word | python-docx + ReportLab | ≥ 1.1.0 / ≥ 4.0 |
| Frontend | HTML5 + CSS3 + JavaScript vanilla | — |
| Empaquetado | PyInstaller (onefile) | — |
| Instalador Windows | Inno Setup | — |

La app no tiene base de datos local. Todo estado de sesión vive en memoria RAM y archivos temporales en disco.

---

## Estructura de carpetas

```
ExpedientGenerator/
├── backend/
│   ├── __init__.py
│   ├── main.py           ← API FastAPI completa (~1300 líneas)
│   ├── models.py         ← Pydantic models (request/response)
│   ├── pdf_processor.py  ← Lógica de fusión, foliación, conversiones
│   └── session_manager.py← Gestión de carpetas temporales
├── frontend/
│   ├── index.html        ← SPA completa (todo en un archivo)
│   ├── app.js            ← Lógica del cliente
│   └── styles.css        ← Estilos
├── launcher.py           ← Launcher simple (dev/fallback)
├── launcher_main.py      ← Launcher real con auto-update (se compila como .exe)
├── docs/                 ← Esta carpeta
├── installer/
│   └── ExpedienteDigital.iss ← Script Inno Setup
├── ExpedienteDigital.spec    ← PyInstaller spec para la app
├── Launcher.spec             ← PyInstaller spec para el launcher
├── build_all.bat             ← Script de build Windows
├── version.txt               ← Versión actual (p.ej. "1.2.1")
└── requirements.txt          ← Dependencias Python
```

### Datos de usuario en producción (Windows)

```
%LOCALAPPDATA%\ExpedienteDigital\
├── version.txt           ← versión instalada (la escribe el launcher al actualizar)
├── config.json           ← carpeta raíz de expedientes, preferencias
├── nombres_usados.json   ← registro local de throttling por nombre (diario)
├── temp/                 ← sesiones temporales durante el procesamiento
│   └── session_<uuid>/
├── expedientes_generados/← PDFs de salida por defecto
└── logs/
    ├── expediente.log    ← log de la app
    └── launcher.log      ← log del launcher
```

---

## Componentes principales

### 1. Launcher (`launcher_main.py` → `ExpedienteDigital.exe`)

Ejecutable pequeño (~8 MB, solo stdlib). El usuario siempre abre este archivo.

Responsabilidades:
- Instancia única vía mutex de Windows (`Global\ExpedienteDigitalLauncher`)
- Comparar versión local (`version.txt`) contra `/api/version/latest` en Railway
- Descargar y reemplazar `ExpedienteDigital_app.exe` si hay actualización
- Lanzar `ExpedienteDigital_app.exe` de forma desacoplada (DETACHED_PROCESS)

### 2. App (`backend/main.py` → `ExpedienteDigital_app.exe`)

Ejecutable grande (~50 MB, incluye Python + todas las dependencias). Contiene:
- Servidor FastAPI corriendo en Uvicorn en un puerto libre (8000–8019)
- Módulos PyMuPDF, Pillow, python-docx, ReportLab empaquetados

El launcher la inicia y luego abre el navegador predeterminado en `http://127.0.0.1:<puerto>`.

### 3. Frontend (HTML/JS/CSS)

SPA sin framework. Se sirve como archivo estático desde la propia app FastAPI. Se comunica con el backend via `fetch()` contra `http://127.0.0.1:<puerto>/api/*`.

---

## Comunicación Launcher → App

```
                     ┌─────────────────────────────────────┐
                     │         ExpedienteDigital.exe         │
                     │           (launcher_main.py)          │
                     └──────────────────┬──────────────────┘
                                        │
             ┌──────────────────────────▼─────────────────────────┐
             │  GET https://railway.app/api/version/latest         │
             │  ← { version, url_descarga, es_obligatoria }        │
             └──────────────────────────┬─────────────────────────┘
                                        │
               ┌────────────────────────▼────────────────────┐
               │ ¿hay actualización y es obligatoria?         │
               │  SÍ → taskkill app.exe → download → replace  │
               │  NO → ¿app ya corriendo en 8000-8019?        │
               │         SÍ → open browser → exit             │
               │         NO → (try silent update) → launch    │
               └────────────────────────┬────────────────────┘
                                        │
                     ┌──────────────────▼──────────────────┐
                     │    subprocess.Popen(app.exe)          │
                     │    DETACHED_PROCESS | CREATE_NO_WINDOW│
                     └──────────────────┬──────────────────┘
                                        │
                     ┌──────────────────▼──────────────────┐
                     │  webbrowser.open(http://127.0.0.1:N) │
                     └─────────────────────────────────────┘
```

### ⚠ Advertencia: actualización silenciosa no aplicada si el app está corriendo

Si el usuario accede a la app via bookmark del navegador (no via el .exe del launcher), la app puede seguir corriendo indefinidamente en una versión vieja. El launcher detecta la instancia en ejecución y abre el navegador sin revisar actualizaciones.

**La única manera de garantizar la actualización** es que `es_obligatoria = true` en la tabla `versiones` del servidor, y que el usuario cierre la app y vuelva a ejecutar el launcher.

---

## Flujo de auto-update paso a paso

```
launcher_main.py::main()

1. Mutex check — si ya hay una instancia del launcher, salir (previene doble clic)

2. _fetch_latest_info()
   → GET /api/version/latest
   ← { version: "1.2.1", url_descarga: "...", es_obligatoria: true }

3. _read_local_version()
   → leer %LOCALAPPDATA%\ExpedienteDigital\version.txt
   ← "1.1.8" (o "0.0.0" si no existe)

4. Comparar versiones (semver tuple comparison)
   hay_update = (1,2,1) > (1,1,8) = True

5a. Si hay_update AND es_obligatoria:
    → _kill_app_if_running()  # taskkill /F /IM ExpedienteDigital_app.exe
    → _do_update(app_exe, url_dl, ver_nueva)
       - Descarga a %LOCALAPPDATA%\ExpedienteDigital\ExpedienteDigital_app.exe.tmp
       - Hasta 3 reintentos con backoff (2s, 4s)
       - Espera hasta 8 intentos para que Windows Defender libere el archivo
       - Renombra .tmp → app.exe
       - Escribe version.txt con la versión nueva
    → Si falla: error dialog, NO lanza app (bloqueo hasta actualizar)

5b. Si hay_update AND NOT es_obligatoria:
    → _find_running_url(): busca app corriendo en puertos 8000-8019
    → Si está corriendo: webbrowser.open(url) → return (no actualiza)
    → Si no está corriendo: _do_update() silencioso (fallo ignorado) → lanzar igual

5c. Sin actualización:
    → _find_running_url() → si está corriendo: open browser → return
    → _launch(app_exe)

6. _launch(app_exe)
   → subprocess.Popen(app.exe, DETACHED | NO_WINDOW)
```

---

## Comunicación App → Servidor de licencias

La app hace llamadas HTTP directas al servidor Railway. No hay proxy ni middleware intermedio.

| Endpoint | Cuándo | Qué hace |
|---|---|---|
| `POST /api/verificar` | Al iniciar la UI (`/api/licencia`) | Verifica si el hardware_id tiene licencia activa |
| `POST /api/expediente/registrar` | Al generar cada expediente | Registra el expediente y descuenta del cupo |
| `GET /api/version/latest` | En cada arranque del launcher | Obtiene la versión más reciente disponible |

El `hardware_id` se calcula localmente una vez: `SHA256(mac_address + processor + platform_info)[:32]`.
