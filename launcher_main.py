"""
Expediente Digital — Launcher
Verifica actualizaciones, reemplaza app.exe (sin locks) y la lanza.
Solo stdlib — tamaño objetivo ~8 MB.
"""

import ctypes
import json
import os
import shutil
import subprocess
import sys
import urllib.request
import webbrowser
from datetime import datetime
from pathlib import Path

# ── Constantes ─────────────────────────────────────────────────────────────────
_LICENSE_SERVER = "https://expediente-licencias-production.up.railway.app"
_APP_EXE        = "ExpedienteDigital_app.exe"
_VERSION_FILE   = "version.txt"
_DETACHED       = 0x00000008   # DETACHED_PROCESS
_NO_WINDOW      = 0x08000000   # CREATE_NO_WINDOW
_MUTEX_NAME     = "Global\\ExpedienteDigitalLauncher"

# ── Instancia única — evita abrir múltiples pestañas si el usuario hace doble clic ─
_mutex_handle = ctypes.windll.kernel32.CreateMutexW(None, True, _MUTEX_NAME)
if ctypes.windll.kernel32.GetLastError() == 183:  # ERROR_ALREADY_EXISTS
    sys.exit(0)

# ── AppData dir (calculado una vez, nivel de módulo) ───────────────────────────
def _make_appdata_dir() -> Path:
    base = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
    d = Path(base) / "ExpedienteDigital"
    d.mkdir(parents=True, exist_ok=True)
    return d

_APP_DIR = _make_appdata_dir()

# ── Log (I/O directa — funciona siempre en frozen exe, sin módulo logging) ────
#
# Se inicializa aquí, al cargar el módulo, antes de que main() corra.
# Así cualquier excepción posterior también queda registrada.
try:
    (_APP_DIR / "logs").mkdir(exist_ok=True)
    _LOG_FILE: Path = _APP_DIR / "logs" / "launcher.log"
except Exception:
    # Fallback absoluto: escritorio del usuario
    _LOG_FILE = Path(os.path.expanduser("~")) / "Desktop" / "launcher.log"

def _log(level: str, msg: str) -> None:
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"{ts}  {level:<7}  {msg}\n"
    try:
        # Rotar si supera 200 KB
        if _LOG_FILE.exists() and _LOG_FILE.stat().st_size > 200_000:
            _LOG_FILE.replace(_LOG_FILE.with_suffix(".log.1"))
        with open(_LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line)
    except Exception:
        pass

# Primera línea siempre escrita al arrancar
_log("INFO", "=== Launcher iniciado ===")
_log("DEBUG", f"log_file: {_LOG_FILE}")
_log("DEBUG", f"app_dir:  {_APP_DIR}")
_log("DEBUG", f"exe:      {sys.executable}")
_log("DEBUG", f"frozen:   {getattr(sys, 'frozen', False)}")


# ── Rutas ──────────────────────────────────────────────────────────────────────

def _launcher_dir() -> Path:
    return Path(sys.executable).parent if getattr(sys, "frozen", False) else Path(__file__).parent


# ── UI mínima (solo errores fatales) ──────────────────────────────────────────

def _err(msg: str) -> None:
    _log("ERROR", msg.replace("\n", " | "))
    try:
        ctypes.windll.user32.MessageBoxW(None, msg, "Expediente Digital", 0x10)
    except Exception:
        print(msg, file=sys.stderr)


# ── Versión ────────────────────────────────────────────────────────────────────

def _ver_tuple(v: str) -> tuple:
    try:
        parts = [int(x) for x in str(v).strip().split(".")]
        while len(parts) < 3:
            parts.append(0)
        return tuple(parts[:3])
    except Exception:
        return (0, 0, 0)


def _read_local_version() -> str:
    p = _APP_DIR / _VERSION_FILE
    try:
        v = p.read_text(encoding="utf-8").strip()
        _log("INFO", f"version.txt existe: '{v}'  →  {_ver_tuple(v)}")
        return v
    except FileNotFoundError:
        _log("INFO", f"version.txt no existe en {p} → asumiendo 0.0.0")
        return "0.0.0"
    except Exception as exc:
        _log("WARNING", f"No se pudo leer version.txt: {exc}")
        return "0.0.0"


def _write_local_version(ver: str) -> None:
    try:
        (_APP_DIR / _VERSION_FILE).write_text(ver, encoding="utf-8")
        _log("INFO", f"version.txt actualizado a '{ver}'")
    except Exception as exc:
        _log("WARNING", f"No se pudo escribir version.txt: {exc}")


# ── Comprobar si la app ya está corriendo ──────────────────────────────────────

def _find_running_url() -> str:
    _log("DEBUG", "Buscando instancia ya en ejecución (puertos 8000-8019)...")
    for port in range(8000, 8020):
        try:
            with urllib.request.urlopen(
                f"http://127.0.0.1:{port}/api/health", timeout=0.3
            ) as r:
                if r.status == 200:
                    url = f"http://127.0.0.1:{port}"
                    _log("INFO", f"App ya corriendo en {url}")
                    return url
        except Exception:
            pass
    _log("DEBUG", "No hay instancia en ejecución")
    return ""


# ── Actualización ──────────────────────────────────────────────────────────────

def _fetch_latest_info() -> dict:
    url = f"{_LICENSE_SERVER}/api/version/latest"
    _log("INFO", f"GET {url}")
    try:
        req = urllib.request.Request(
            url, headers={"User-Agent": "ExpedienteDigital-Launcher/2.0"}
        )
        with urllib.request.urlopen(req, timeout=8) as r:
            raw = r.read().decode("utf-8")
            data = json.loads(raw)
            _log("INFO", f"Respuesta servidor: {raw.strip()}")
            return data
    except urllib.error.URLError as exc:
        _log("WARNING", f"Sin conexión al servidor: {exc}")
        return {}
    except Exception as exc:
        _log("WARNING", f"Error consultando servidor: {exc}")
        return {}


def _download_app(url: str, dst: Path) -> None:
    if url.startswith("/"):
        url = f"{_LICENSE_SERVER}{url}"
    _log("INFO", f"Descargando: {url}")
    req = urllib.request.Request(url, headers={"User-Agent": "ExpedienteDigital-Launcher/2.0"})
    with urllib.request.urlopen(req, timeout=180) as resp, open(dst, "wb") as f:
        shutil.copyfileobj(resp, f)
    size_mb = dst.stat().st_size / 1_048_576
    _log("INFO", f"Descarga completa: {size_mb:.1f} MB → {dst}")


def _kill_app_if_running() -> None:
    """Termina ExpedienteDigital_app.exe si está corriendo (necesario para reemplazar el exe)."""
    try:
        subprocess.run(
            ["taskkill", "/F", "/IM", _APP_EXE],
            capture_output=True,
            creationflags=_NO_WINDOW,
        )
        _log("INFO", "Proceso de app terminado para actualización obligatoria")
        import time; time.sleep(1)  # dar tiempo al SO para liberar el archivo
    except Exception as exc:
        _log("WARNING", f"taskkill falló: {exc}")


def _do_update(app_exe: Path, url_dl: str, ver_nueva: str) -> bool:
    """Descarga y reemplaza app.exe con reintentos. Devuelve True si tuvo éxito."""
    if not url_dl:
        _log("WARNING", "url_descarga vacía — cancelando descarga")
        return False
    import time as _t
    tmp = _APP_DIR / f"{_APP_EXE}.tmp"
    for attempt in range(1, 4):
        try:
            _log("INFO", f"Descarga intento {attempt}/3")
            _download_app(url_dl, tmp)
            # Esperar a que Windows Defender libere el archivo tras escanearlo
            for rename_try in range(8):
                try:
                    tmp.replace(app_exe)
                    break
                except OSError:
                    if rename_try == 7:
                        raise
                    _t.sleep(1.5)
            _write_local_version(ver_nueva)
            _log("INFO", f"Actualización instalada correctamente: {ver_nueva}")
            return True
        except Exception as exc:
            _log("WARNING", f"Intento {attempt}/3 falló: {exc}")
            try:
                tmp.unlink(missing_ok=True)
            except Exception:
                pass
            if attempt < 3:
                _t.sleep(2 ** attempt)  # backoff: 2s, 4s
    _log("ERROR", "Todos los intentos de descarga fallaron")
    return False


# ── Lanzar app.exe ─────────────────────────────────────────────────────────────

def _launch(app_exe: Path) -> None:
    _log("INFO", f"Lanzando: {app_exe}")
    subprocess.Popen(
        [str(app_exe)],
        cwd=str(app_exe.parent),
        creationflags=_DETACHED | _NO_WINDOW,
        close_fds=True,
    )
    _log("INFO", "App lanzada — launcher terminando")


# ── Main ───────────────────────────────────────────────────────────────────────

def main() -> None:
    try:
        app_exe = _APP_DIR / _APP_EXE

        # 1. Primera instalación: copiar app.exe desde la carpeta del launcher
        if not app_exe.exists():
            _log("INFO", "app.exe no encontrada en AppData — primera instalación")
            sibling = _launcher_dir() / _APP_EXE
            _log("DEBUG", f"Buscando sibling en: {sibling}")
            if sibling.exists():
                try:
                    shutil.copy2(sibling, app_exe)
                    _log("INFO", f"app.exe copiada desde {sibling}")
                except Exception as exc:
                    _err(
                        f"No se pudo instalar la aplicación en AppData:\n\n{exc}\n\n"
                        "Intenta ejecutar como administrador."
                    )
                    return
            else:
                _log("ERROR", f"Sibling no encontrado: {sibling}")
                _err(
                    f"No se encontró {_APP_EXE} junto al launcher.\n\n"
                    "Descarga el paquete completo desde la página oficial."
                )
                return

        # 2. Consultar servidor (siempre, antes de ver si la app está corriendo)
        info        = _fetch_latest_info()
        ver_nueva   = (info.get("version") or "").strip()
        ver_local   = _read_local_version()
        obligatoria = bool(info.get("es_obligatoria", False))
        hay_update  = bool(ver_nueva and _ver_tuple(ver_nueva) > _ver_tuple(ver_local))

        _log("INFO", f"local={ver_local}  servidor={ver_nueva or '(vacío)'}  obligatoria={obligatoria}  hay_update={hay_update}")

        if hay_update and obligatoria:
            # Matar app siempre antes de reemplazar el exe
            _kill_app_if_running()

            url_dl = (info.get("url_descarga") or "").strip()
            ok = _do_update(app_exe, url_dl, ver_nueva)
            if not ok:
                _err(
                    f"Se requiere la versión {ver_nueva} para continuar.\n\n"
                    "No se pudo descargar la actualización.\n"
                    "Verifica tu conexión a internet e intenta de nuevo."
                )
                return  # bloquear acceso hasta que actualice

        else:
            # Sin update obligatorio: si ya está corriendo, abrir navegador y salir
            running_url = _find_running_url()
            if running_url:
                webbrowser.open(running_url)
                return

            # Update opcional disponible: intentar silencioso
            if hay_update:
                url_dl = (info.get("url_descarga") or "").strip()
                _do_update(app_exe, url_dl, ver_nueva)

        # 3. Lanzar app.exe
        _launch(app_exe)

    except Exception as exc:
        _log("CRITICAL", f"Excepción no manejada en main(): {exc}")
        import traceback
        _log("CRITICAL", traceback.format_exc().replace("\n", " | "))
        _err(f"Error inesperado al iniciar:\n\n{exc}\n\nRevisa:\n{_LOG_FILE}")


if __name__ == "__main__":
    main()
