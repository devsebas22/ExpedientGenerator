# Build y Deploy — Expediente Digital

## Requisitos previos (máquina de build Windows)

- Python 3.11+ con `pip install -r requirements.txt`
- PyInstaller: `pip install pyinstaller`
- Inno Setup (opcional, para el instalador): https://jrsoftware.org/isdl.php

---

## Compilar

```bat
.\build_all.bat
```

El script ejecuta tres pasos en orden:

### Paso 1 — App principal
```bat
python -m PyInstaller ExpedienteDigital.spec --noconfirm
```
Genera `dist\ExpedienteDigital_app.exe` (~50 MB). Incluye Python runtime, FastAPI, PyMuPDF, Pillow, python-docx, ReportLab y el frontend HTML/JS/CSS empaquetado en `_MEIPASS`.

### Paso 2 — Launcher
```bat
python -m PyInstaller Launcher.spec --noconfirm
```
Genera `dist\ExpedienteDigital.exe` (~8 MB, solo stdlib). El launcher nunca incluye dependencias de terceros — solo lo que viene con Python puro.

### Paso 3 — Instalador (opcional)
```bat
iscc installer\ExpedienteDigital.iss
```
Si Inno Setup está disponible, genera `dist\installer\ExpedienteDigital_Setup.exe`. Si no está, el script muestra una advertencia pero los `.exe` de `dist\` ya están listos para distribuir como `.zip`.

---

## Estructura de salida

```
dist/
├── ExpedienteDigital.exe      ← launcher (el usuario ejecuta ESTE)
├── ExpedienteDigital_app.exe  ← app (se copia a AppData, no se ejecuta directo)
└── installer/
    └── ExpedienteDigital_Setup.exe  ← instalador tradicional (opcional)
```

---

## Publicar una nueva versión

### 1. Actualizar el número de versión

Editar `version.txt` en la raíz del repo:
```
1.2.2
```

### 2. Compilar

```bat
.\build_all.bat
```

### 3. Subir el ejecutable a GitHub Releases

1. Ir a https://github.com/devsebas22/ExpedientGenerator/releases/new
2. Crear tag `v1.2.2`
3. Adjuntar `dist\ExpedienteDigital_app.exe` (solo el app, no el launcher)
4. Copiar la URL de descarga directa, formato:
   ```
   https://github.com/devsebas22/ExpedientGenerator/releases/download/v1.2.2/ExpedienteDigital_app.exe
   ```

### 4. Registrar la versión en el panel admin

1. Entrar al panel de licencias en Railway
2. Ir a **Versiones** → **Nueva versión**
3. Completar:
   - `Versión`: `1.2.2`
   - `URL de descarga`: la URL de GitHub copiada en el paso anterior
   - `Es obligatoria`: ✅ recomendado siempre activar para no dejar máquinas en versiones viejas
4. Hacer clic en **Activar** para marcarla como la versión activa

> ⚠ **Importante**: Si `es_obligatoria` queda en `false`, las máquinas que tengan la app corriendo en ese momento NO se actualizarán en esa sesión. Solo se actualizarán si:
> - El usuario cierra la app completamente
> - Abre el `ExpedienteDigital.exe` (launcher) de nuevo
> - Y el launcher no detecta la app corriendo al momento de iniciar
>
> Para garantizar que todas las máquinas actualicen, marcar siempre como obligatoria.

---

## Cómo funciona el auto-update del launcher — paso a paso

```
Al ejecutar ExpedienteDigital.exe:

1. Verifica instancia única (mutex Windows)
   Si ya hay un launcher corriendo → salir

2. Consulta versión en el servidor
   GET https://expediente-licencias-production.up.railway.app/api/version/latest
   ← { version: "1.2.2", url_descarga: "...", es_obligatoria: true }

3. Lee version.txt local
   %LOCALAPPDATA%\ExpedienteDigital\version.txt → "1.2.1"

4. Compara versiones (tuple semver)
   (1,2,2) > (1,2,1) → hay_update = True

5a. Actualización OBLIGATORIA (es_obligatoria = true):
    a. taskkill /F /IM ExpedienteDigital_app.exe (si estaba corriendo)
    b. Descarga app.exe → app.exe.tmp (hasta 3 reintentos, backoff 2s/4s)
    c. Espera liberación del antivirus (hasta 8 intentos × 1.5s)
    d. Renombra .tmp → app.exe atómicamente
    e. Escribe version.txt = "1.2.2"
    f. Si falla: muestra error y NO lanza la app (usuario queda bloqueado)

5b. Actualización OPCIONAL (es_obligatoria = false):
    a. Busca app corriendo en puertos 8000-8019
       → SI está corriendo: abre navegador, sale. NO actualiza.   ← ⚠ Advertencia
       → Si no está corriendo: intenta descarga silenciosa
    b. Lanza la app (con la versión que haya, actualizada o no)

6. subprocess.Popen(app.exe, DETACHED_PROCESS | CREATE_NO_WINDOW)
   El launcher termina. La app sigue corriendo independientemente.
```

### ⚠ Caso crítico: app corriendo + actualización no obligatoria

Si el usuario tiene la app abierta (accede por bookmark del navegador, no por el launcher) y la actualización no es obligatoria, el launcher detecta la instancia corriendo y abre el navegador sin actualizar. La versión vieja sigue corriendo indefinidamente.

**Solución:** marcar todas las versiones como `es_obligatoria = true` en el panel.

---

## Distribución de una instalación nueva

Para una máquina que instala la app por primera vez (sin versión previa):

1. Entregar solo `ExpedienteDigital.exe` (el launcher, ~8 MB)
2. Al ejecutarlo, si no encuentra `ExpedienteDigital_app.exe` en AppData:
   - Busca un `ExpedienteDigital_app.exe` en la misma carpeta del launcher (sibling)
   - Si no lo encuentra: muestra diálogo "Descargando Expediente Digital…" y descarga desde el servidor
3. Lanza la app, que en el primer arranque crea las carpetas necesarias y abre la interfaz

El usuario no necesita instalar Python ni ninguna dependencia.
