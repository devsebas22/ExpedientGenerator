# 📁 Expediente Digital

Expediente Digital es una aplicación local para generar expedientes a partir
de múltiples PDFs. La aplicación permite subir y ordenar documentos, fusionarlos
por lotes y añadir numeración de página (folio) sin rasterizar el contenido.

---

## Características

- Interfaz web ligera con carga por arrastrar y soltar.
- Admite selección de archivos individuales o carpetas completas.
- Reordenado manual de archivos por arrastre.
- Configuración de posición de folio, tamaño de fuente y márgenes.
- Proceso de generación con barra de progreso y descarga directa.
- Registro de actividad en `logs/expediente.log`.

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
├── expedientes_generados/   ← PDFs generados
├── temp/                    ← archivos temporales
├── logs/                    ← registros de ejecución
├── requirements.txt
└── run.py                   ← lanzador local
```

---

## Instalación

### Requisitos

- Python 3.10 o superior
- `pip`

### Pasos

```bash
cd expediente
python3 -m venv .venv
source .venv/bin/activate        # Linux/Mac/WSL
# .venv\Scripts\activate      # Windows CMD
# .venv\Scripts\Activate.ps1  # Windows PowerShell
pip install -r requirements.txt
```

---

## Ejecución

```bash
python3 run.py
```

Esto levanta el servidor en `http://127.0.0.1:8000` y abre la aplicación en el
navegador por defecto.

### Opciones del lanzador

```bash
python3 run.py --port 8080
python3 run.py --no-browser
python3 run.py --host 0.0.0.0
```

### Arranque manual sin `run.py`

```bash
python3 -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

---

## Uso

1. Arrastra PDFs al área de carga o selecciona archivos desde el explorador.
2. Carga una carpeta completa escribiendo su ruta o usando el selector de
   carpetas.
3. Reordena los documentos arrastrando las filas en la lista.
4. Ajusta la posición del folio, tamaño de fuente y márgenes.
5. Presiona **Generar expediente** y sigue el progreso.
6. Descarga el resultado o encuentra el PDF en `expedientes_generados/`.

---

## API endpoints

| Método    | Ruta | Descripción |
|-----------|------|-------------|
| `GET`     | `/` | Sirve la interfaz web |
| `POST`    | `/api/upload` | Sube un PDF (multipart) |
| `POST`    | `/api/load-folder` | Carga PDFs desde una ruta local |
| `POST`    | `/api/process` | Inicia la fusión y foliado |
| `GET`     | `/api/task/{id}` | Consulta el estado del proceso |
| `GET`     | `/api/download/{filename}` | Descarga el expediente generado |
| `DELETE`  | `/api/files/{id}` | Elimina un archivo subido |
| `POST`    | `/api/cleanup` | Limpia archivos temporales |
| `GET`     | `/api/health` | Verifica que el servicio está activo |

---

## Notas técnicas

- PyMuPDF agrega numeración de página como texto vectorial, sin degradar
  la calidad del PDF.
- El procesamiento se realiza por página para manejar archivos grandes de
  forma eficiente.
- Si un archivo falla, se reporta en la interfaz y el resto del expediente
  continúa generándose.
- Para PDFs encriptados, el servicio prueba contraseña vacía y omite el
  archivo si no puede leerlo.
- Los registros se almacenan en `logs/expediente.log`.
