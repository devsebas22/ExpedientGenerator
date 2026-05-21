#!/bin/bash
# ── Build de Expediente Digital ──────────────────────────────────────────────
# Requisitos: pip install pyinstaller requests

set -e
echo ""
echo " Compilando Expediente Digital..."
echo ""

pyinstaller \
  --onefile \
  --windowed \
  --name "ExpedienteDigital" \
  --add-data "frontend:frontend" \
  --hidden-import "backend.main" \
  --hidden-import "backend.models" \
  --hidden-import "backend.pdf_processor" \
  --hidden-import "backend.session_manager" \
  run.py

echo ""
echo " ✅  Listo. El binario está en dist/ExpedienteDigital"
echo ""
