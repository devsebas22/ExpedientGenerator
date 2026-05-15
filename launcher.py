"""
Launcher para Expediente Digital.
Funciona tanto como script de desarrollo como .exe de PyInstaller (onefile).
"""
import os
import socket
import sys
import threading
import time
import webbrowser
from pathlib import Path

# ── Detección de entorno ──────────────────────────────────────────────────────
_FROZEN = getattr(sys, "frozen", False)

if _FROZEN:
    # Modo .exe: datos en AppData\Local\ExpedienteDigital — nunca junto al .exe,
    # sin importar si está en el escritorio, descargas u otra carpeta.
    _local = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
    BASE_DIR = Path(_local) / "ExpedienteDigital"
else:
    # Modo desarrollo: raíz del proyecto
    BASE_DIR = Path(__file__).parent

BASE_DIR.mkdir(parents=True, exist_ok=True)

# Crear carpetas de trabajo en AppData (si no existen)
for _folder in ("temp", "logs", "expedientes_generados"):
    (BASE_DIR / _folder).mkdir(exist_ok=True)

# ── Config ────────────────────────────────────────────────────────────────────
HOST = "127.0.0.1"
_server_error: list = []   # captura errores del hilo servidor


def _find_free_port(start: int = 8000) -> int:
    """Primer puerto disponible en el rango [start, start+20)."""
    for port in range(start, start + 20):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex((HOST, port)) != 0:
                return port
    return start


def _wait_for_server(url: str, timeout: int = 30) -> bool:
    """Espera hasta que GET /api/health devuelva 200, o se agote el tiempo."""
    import urllib.request
    deadline = time.time() + timeout
    while time.time() < deadline:
        if _server_error:          # el hilo ya murió con error — no esperar más
            return False
        try:
            urllib.request.urlopen(f"{url}/api/health", timeout=1)
            return True
        except Exception:
            time.sleep(0.3)
    return False


def _show_error(title: str, message: str) -> None:
    """Cuadro de diálogo de error en Windows, sin consola ni tkinter."""
    try:
        import ctypes
        ctypes.windll.user32.MessageBoxW(None, message, title, 0x10)
    except Exception:
        print(f"[ERROR] {title}: {message}", file=sys.stderr)


def _run_server(port: int) -> None:
    """Arranca uvicorn en el hilo actual. Captura cualquier excepción fatal."""
    try:
        import uvicorn
        from backend.main import app  # importación directa — funciona en frozen
        uvicorn.run(
            app,
            host=HOST,
            port=port,
            log_level="warning",
            # log_config=None evita que uvicorn llame a logging.config.dictConfig
            # con su configuración interna, que usa clases por string
            # ("uvicorn.logging.DefaultFormatter") y falla en PyInstaller frozen mode
            # con el error "Unable to configure formatter 'default'".
            # Al pasar None, uvicorn no toca el sistema de logging — el nuestro
            # (configurado en backend/main.py: _setup_logging) se encarga de todo.
            log_config=None,
        )
    except Exception as exc:
        _server_error.append(str(exc))


def main() -> None:
    port = _find_free_port()
    url  = f"http://{HOST}:{port}"

    # Hilo daemon: muere automáticamente cuando el usuario cierra el proceso
    server_thread = threading.Thread(target=_run_server, args=(port,), daemon=True)
    server_thread.start()

    # Esperar a que el servidor esté listo
    if not _wait_for_server(url, timeout=30):
        detail = _server_error[0] if _server_error else "Tiempo de espera agotado."
        _show_error(
            "Expediente Digital — Error de inicio",
            f"El servidor no pudo iniciarse.\n\n"
            f"Detalle: {detail}\n\n"
            f"Revisa el archivo:\n{BASE_DIR / 'logs' / 'expediente.log'}",
        )
        sys.exit(1)

    # Abrir la interfaz en el navegador predeterminado
    webbrowser.open(url)

    # Mantener el proceso vivo mientras el servidor esté corriendo
    try:
        server_thread.join()
    except KeyboardInterrupt:
        pass

    # Si el servidor murió inesperadamente, avisar
    if _server_error:
        _show_error(
            "Expediente Digital — Error inesperado",
            f"El servidor se detuvo inesperadamente.\n\n"
            f"Detalle: {_server_error[0]}\n\n"
            f"Revisa: {BASE_DIR / 'logs' / 'expediente.log'}",
        )


if __name__ == "__main__":
    main()
