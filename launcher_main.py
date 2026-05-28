"""
Expediente Digital — Launcher
Lee versión, verifica update, reemplaza app.exe si hay uno nuevo (no está en
ejecución en ese momento → sin locks de DLL), y lanza app.exe.

Compilado sin dependencias externas: solo stdlib.  Tamaño objetivo ~8 MB.
"""

import ctypes
import json
import os
import shutil
import subprocess
import sys
import urllib.request
import webbrowser
from pathlib import Path

# ── Constantes ─────────────────────────────────────────────────────────────────
_LICENSE_SERVER = "https://expediente-licencias-production.up.railway.app"
_APP_EXE        = "ExpedienteDigital_app.exe"
_VERSION_FILE   = "version.txt"
_DETACHED       = 0x00000008   # DETACHED_PROCESS
_NO_WINDOW      = 0x08000000   # CREATE_NO_WINDOW


# ── Rutas ──────────────────────────────────────────────────────────────────────

def _appdata_dir() -> Path:
    """Carpeta de datos en AppData — igual que usa la app internamente."""
    base = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
    d = Path(base) / "ExpedienteDigital"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _launcher_dir() -> Path:
    """Carpeta donde vive el launcher (junto a app.exe en la distribución inicial)."""
    return Path(sys.executable).parent if getattr(sys, "frozen", False) else Path(__file__).parent


# ── UI mínima (solo errores fatales) ──────────────────────────────────────────

def _err(msg: str) -> None:
    try:
        ctypes.windll.user32.MessageBoxW(None, msg, "Expediente Digital", 0x10)
    except Exception:
        print(msg, file=sys.stderr)


# ── Versión ────────────────────────────────────────────────────────────────────

def _ver_tuple(v: str) -> tuple:
    try:
        return tuple(int(x) for x in str(v).split("."))
    except Exception:
        return (0,)


def _read_local_version(app_dir: Path) -> str:
    p = app_dir / _VERSION_FILE
    try:
        return p.read_text(encoding="utf-8").strip()
    except Exception:
        return "0.0.0"


def _write_local_version(app_dir: Path, ver: str) -> None:
    try:
        (app_dir / _VERSION_FILE).write_text(ver, encoding="utf-8")
    except Exception:
        pass


# ── Comprobar si la app ya está corriendo ──────────────────────────────────────

def _find_running_url() -> str:
    """Escanea puertos 8000–8019 buscando el servidor local de la app."""
    for port in range(8000, 8020):
        try:
            with urllib.request.urlopen(
                f"http://127.0.0.1:{port}/api/health", timeout=0.3
            ) as r:
                if r.status == 200:
                    return f"http://127.0.0.1:{port}"
        except Exception:
            pass
    return ""


# ── Actualización ──────────────────────────────────────────────────────────────

def _fetch_latest_info() -> dict:
    try:
        req = urllib.request.Request(
            f"{_LICENSE_SERVER}/api/version/latest",
            headers={"User-Agent": "ExpedienteDigital-Launcher/2.0"},
        )
        with urllib.request.urlopen(req, timeout=6) as r:
            return json.loads(r.read().decode("utf-8"))
    except Exception:
        return {}


def _download_app(url: str, dst: Path) -> None:
    """Descarga url → dst.  Lanza excepción si falla."""
    if url.startswith("/"):
        url = f"{_LICENSE_SERVER}{url}"
    req = urllib.request.Request(url, headers={"User-Agent": "ExpedienteDigital-Launcher/2.0"})
    with urllib.request.urlopen(req, timeout=180) as resp, open(dst, "wb") as f:
        shutil.copyfileobj(resp, f)


def _try_update(app_dir: Path, app_exe: Path) -> None:
    """Verifica e instala actualización de app.exe de forma silenciosa."""
    info      = _fetch_latest_info()
    ver_nueva = info.get("version") or ""
    ver_local = _read_local_version(app_dir)

    if not ver_nueva or _ver_tuple(ver_nueva) <= _ver_tuple(ver_local):
        return  # sin novedad

    url_dl = info.get("url_descarga") or ""
    if not url_dl:
        return

    tmp = app_dir / f"{_APP_EXE}.tmp"
    try:
        _download_app(url_dl, tmp)
        # app.exe NO está en ejecución aquí → replace() sin locks de DLL
        tmp.replace(app_exe)
        _write_local_version(app_dir, ver_nueva)
    except Exception:
        # Fallo silencioso: la versión anterior sigue disponible
        try:
            tmp.unlink(missing_ok=True)
        except Exception:
            pass


# ── Lanzar app.exe ─────────────────────────────────────────────────────────────

def _launch(app_exe: Path) -> None:
    subprocess.Popen(
        [str(app_exe)],
        cwd=str(app_exe.parent),
        creationflags=_DETACHED | _NO_WINDOW,
        close_fds=True,
    )


# ── Main ───────────────────────────────────────────────────────────────────────

def main() -> None:
    app_dir = _appdata_dir()
    app_exe = app_dir / _APP_EXE

    # 1. ¿La app ya está corriendo? → abrir el navegador y salir
    running_url = _find_running_url()
    if running_url:
        webbrowser.open(running_url)
        return

    # 2. Primera instalación: copiar app.exe desde la carpeta del launcher
    if not app_exe.exists():
        sibling = _launcher_dir() / _APP_EXE
        if sibling.exists():
            try:
                shutil.copy2(sibling, app_exe)
            except Exception as exc:
                _err(
                    f"No se pudo instalar la aplicación en AppData:\n\n{exc}\n\n"
                    f"Intenta ejecutar como administrador."
                )
                return
        else:
            _err(
                f"No se encontró {_APP_EXE} junto al launcher.\n\n"
                "Descarga el paquete completo desde la página oficial."
            )
            return

    # 3. Verificar e instalar actualización (silencioso, app.exe no está corriendo)
    _try_update(app_dir, app_exe)

    # 4. Lanzar app.exe — el launcher sale; app.exe corre de forma independiente
    try:
        _launch(app_exe)
    except Exception as exc:
        _err(f"No se pudo iniciar la aplicación:\n\n{exc}")


if __name__ == "__main__":
    main()
