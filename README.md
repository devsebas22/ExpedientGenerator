# Expediente Digital

Aplicación de escritorio para Windows que fusiona múltiples PDFs (y convierte imágenes y documentos Word) en un único expediente foliado. Distribuida como un `.exe` con actualización automática.

El backend es un servidor FastAPI local que corre en la máquina del usuario; el frontend es HTML/JS/CSS puro servido por ese mismo servidor. El usuario accede a la app desde el navegador en `localhost`.

---

## Cómo levantar en desarrollo local

### Requisitos

- Python 3.10+
- `pip`

### Pasos

```bash
cd expediente
python3 -m venv .venv
source .venv/bin/activate      # Linux/Mac/WSL
# .venv\Scripts\activate       # Windows CMD
pip install -r requirements.txt
python3 run.py
```

La app queda disponible en `http://127.0.0.1:8000` y se abre en el navegador automáticamente.

### Variables de entorno (opcionales en local)

```
LICENSE_SERVER_URL=https://expediente-licencias-production.up.railway.app
```

Si no están definidas, la verificación de licencia y el registro de expedientes se omiten silenciosamente — útil para desarrollo.

---

## Estructura

```
expediente/
├── backend/
│   ├── main.py           ← API FastAPI (endpoints, registro de licencia)
│   ├── pdf_processor.py  ← fusión, foliación, conversión de imágenes y Word
│   └── models.py         ← esquemas Pydantic
├── frontend/
│   ├── index.html
│   ├── styles.css
│   └── app.js
├── launcher_main.py       ← launcher Windows (auto-update, instancia única)
├── run.py                 ← lanzador local de desarrollo
├── requirements.txt
├── ExpedienteDigital.spec ← spec PyInstaller para la app
├── Launcher.spec          ← spec PyInstaller para el launcher
├── build_all.bat          ← compila app + launcher + instalador (Windows)
├── version.txt            ← versión actual (leída por el launcher)
└── docs/                  ← documentación técnica
```

---

## Compilar y distribuir

Ver [`docs/BUILD_Y_DEPLOY.md`](docs/BUILD_Y_DEPLOY.md) para el proceso completo de compilación con PyInstaller y publicación de versiones.

---

## Documentación técnica

| Documento | Contenido |
|---|---|
| [`docs/ARQUITECTURA.md`](docs/ARQUITECTURA.md) | Stack, componentes, flujo de datos, auto-update |
| [`docs/FUNCIONES.md`](docs/FUNCIONES.md) | Referencia de funciones principales del backend |
| [`docs/BUILD_Y_DEPLOY.md`](docs/BUILD_Y_DEPLOY.md) | Compilación, PyInstaller, publicación de versiones |
