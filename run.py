#!/usr/bin/env python3
"""
Lanzador de Expediente Digital.
Uso:
    python run.py               # inicia el servidor en puerto 8000
    python run.py --port 8080   # puerto personalizado
    python run.py --no-browser  # no abrir navegador automáticamente
"""
import argparse
import os
import subprocess
import sys
import time
import webbrowser
from pathlib import Path

ROOT = Path(__file__).parent


def main() -> None:
    parser = argparse.ArgumentParser(description="Expediente Digital")
    parser.add_argument("--port",       type=int, default=8000)
    parser.add_argument("--host",       default="127.0.0.1")
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args()

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
