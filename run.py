#!/usr/bin/env python3
"""
Lanzador de Expediente Digital.
Uso:
    python run.py               # inicia el servidor en puerto 8000
    python run.py --port 8080   # puerto personalizado
    python run.py --no-browser  # no abrir navegador automáticamente
"""
import argparse
import hashlib
import os
import platform
import subprocess
import sys
import time
import uuid
import webbrowser
from pathlib import Path

ROOT = Path(__file__).parent

# ── URL del servidor de licencias (actualizar tras el deploy en Railway) ───────
LICENSE_SERVER = "https://TU_APP.up.railway.app"


def get_hardware_id() -> str:
    mac = ':'.join(
        ['{:02x}'.format((uuid.getnode() >> ele) & 0xff) for ele in range(0, 8*6, 8)][::-1]
    )
    cpu    = platform.processor()
    sistema = platform.system() + platform.version()
    raw    = f"{mac}-{cpu}-{sistema}"
    return hashlib.sha256(raw.encode()).hexdigest()[:32]


def verificar_licencia() -> None:
    import requests  # importación tardía — no disponible en el scope global al compilar

    hardware_id = get_hardware_id()
    print(f"\n{'─'*52}")
    print("  Verificando licencia…")

    try:
        resp = requests.post(
            f"{LICENSE_SERVER}/api/verificar",
            json={"hardware_id": hardware_id},
            timeout=8,
        )
        data = resp.json()

        if data.get("activa"):
            print(f"  ✅  {data.get('mensaje', 'Licencia activa')}")
            print(f"{'─'*52}\n")
            return

        # Licencia inactiva o vencida
        print(f"\n  ❌  Licencia inactiva o vencida.")
        print(f"  {data.get('mensaje', '')}")
        print(f"\n  Tu Hardware ID:")
        print(f"  {hardware_id}")
        print(f"\n  Contacta a Sebastian Mogollon para activar tu licencia.")
        print(f"  Email: sebastianmogollon055@gmail.com")
        print(f"{'─'*52}")
        input("\nPresiona Enter para salir...")
        sys.exit(1)

    except requests.exceptions.ConnectionError:
        print(f"\n  ⚠️   Sin conexión a internet.")
        print(f"  Verifica tu red e intenta de nuevo.")
        print(f"{'─'*52}")
        input("\nPresiona Enter para salir...")
        sys.exit(1)

    except Exception as e:
        print(f"\n  ❌  Error de verificación: {e}")
        print(f"{'─'*52}")
        input("\nPresiona Enter para salir...")
        sys.exit(1)


def main() -> None:
    parser = argparse.ArgumentParser(description="Expediente Digital")
    parser.add_argument("--port",       type=int, default=8000)
    parser.add_argument("--host",       default="127.0.0.1")
    parser.add_argument("--no-browser", action="store_true")
    parser.add_argument("--skip-license", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()

    if not args.skip_license:
        verificar_licencia()

    # Ensure output and temp directories exist
    (ROOT / "expedientes_generados").mkdir(exist_ok=True)
    (ROOT / "temp").mkdir(exist_ok=True)
    (ROOT / "logs").mkdir(exist_ok=True)

    url = f"http://{args.host}:{args.port}"
    print(f"\n{'─'*50}")
    print("  📁  Expediente Digital")
    print(f"{'─'*50}")
    print(f"  URL  : {url}")
    print(f"  Salida: expedientes_generados/")
    print("  Para detener: Ctrl+C")
    print(f"{'─'*50}\n")

    cmd = [
        sys.executable, "-m", "uvicorn",
        "backend.main:app",
        "--host", args.host,
        "--port", str(args.port),
    ]

    proc = subprocess.Popen(cmd, cwd=str(ROOT))

    if not args.no_browser:
        time.sleep(1.5)
        webbrowser.open(url)

    try:
        proc.wait()
    except KeyboardInterrupt:
        print("\nDeteniendo servidor…")
        proc.terminate()
        proc.wait()
        print("Servidor detenido.")


if __name__ == "__main__":
    main()
