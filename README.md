# 📁 Expediente Digital

Aplicación local para construir expedientes digitales: une múltiples PDFs,
los ordena automáticamente y folea todas las páginas con un número en
la esquina superior derecha.

---

## Estructura del proyecto

```
expediente/
├── backend/
│   ├── __init__.py
│   ├── main.py           ← API FastAPI
│   ├── models.py         ← esquemas Pydantic
│   └── pdf_processor.py  ← lógica de fusión y foliado
├── frontend/
│   ├── index.html
│   ├── styles.css
│   └── app.js
├── expedientes_generados/   ← PDFs finales (se crea sola)
├── temp/                    ← archivos temporales (se crea sola)
├── logs/                    ← expediente.log (se crea solo)
├── requirements.txt
└── run.py                ← lanzador
```

---

## Instalación

### Requisitos

- Python 3.10 o superior
- `pip`

### Pasos

```bash
# 1. Clona o copia el proyecto
cd expediente

# 2. (Opcional pero recomendado) Crea un entorno virtual
python3 -m venv .venv
source .venv/bin/activate          # Linux/Mac/WSL
# .venv\Scripts\activate           # Windows CMD
# .venv\Scripts\Activate.ps1       # Windows PowerShell

# 3. Instala dependencias
pip install -r requirements.txt
```

---

## Ejecución

```bash
python3 run.py
```

Abre automáticamente `http://127.0.0.1:8000` en el navegador.

### Opciones del lanzador

```bash
python3 run.py --port 8080        # cambiar puerto
python3 run.py --no-browser       # no abrir navegador
python3 run.py --host 0.0.0.0     # escuchar en toda la red local
```

### Arranque manual sin run.py

```bash
python3 -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

---

## Uso

1. **Arrastrar PDFs** al área central o usar los botones de selección.
2. **Seleccionar carpeta** desde el explorador (botón) o escribir la ruta
   completa en el campo de texto y pulsar "Cargar".
3. **Reordenar** las filas arrastrándolas si es necesario.
4. **Configurar** posición del folio, tamaño de letra y márgenes.
5. Pulsar **"Generar expediente"** y esperar la barra de progreso.
6. Descargar el PDF con **"Descargar"** o encontrarlo en `expedientes_generados/`.

---

## Empaquetar como .exe (PyInstaller)

```bash
pip install pyinstaller

pyinstaller \
  --onefile \
  --name "ExpedienteDigital" \
  --add-data "frontend:frontend" \
  --add-data "backend:backend" \
  run.py
```

El ejecutable queda en `dist/ExpedienteDigital` (Linux) o
`dist/ExpedienteDigital.exe` (Windows).

> **Nota Windows:** usa `;` como separador en `--add-data`:
> `--add-data "frontend;frontend" --add-data "backend;backend"`

Para crear un instalador NSIS o InnoSetup, apunta el instalador al
archivo `dist/ExpedienteDigital.exe`.

---

## API endpoints

| Método | Ruta | Descripción |
|--------|------|-------------|
| `GET`  | `/` | Sirve la interfaz web |
| `POST` | `/api/upload` | Sube un PDF (multipart) |
| `POST` | `/api/load-folder` | Carga todos los PDFs de una ruta local |
| `POST` | `/api/process` | Inicia la fusión + foliado |
| `GET`  | `/api/task/{id}` | Estado del proceso (polling) |
| `GET`  | `/api/download/{filename}` | Descarga el expediente generado |
| `DELETE` | `/api/files/{id}` | Elimina un archivo subido |
| `POST` | `/api/cleanup` | Limpia todos los archivos temporales |
| `GET`  | `/api/health` | Verificación de estado |

---

## Notas técnicas

- **Sin rasterización**: PyMuPDF añade el número de página como texto
  vectorial sobre el contenido original. La calidad del PDF no cambia.
- **Archivos grandes**: el motor opera página a página mediante lazy loading.
  Funciona con expedientes de 1 000+ páginas y archivos de 200 MB+.
- **PDFs corruptos**: si un archivo falla, se reporta en la interfaz y el
  resto del expediente se genera igualmente.
- **PDFs encriptados**: se intenta desencriptar con contraseña vacía;
  si falla, el archivo se omite y se lista como error.
- **Logs**: toda la actividad queda registrada en `logs/expediente.log`.
