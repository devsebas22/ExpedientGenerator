#!/bin/bash
# ── Build completo desde WSL: launcher + app ───────────────────────────────

set -e
cd "$(dirname "$0")"

echo ""
echo " [1/3] Compilando app (ExpedienteDigital_app.exe)..."
echo ""
python.exe -m PyInstaller ExpedienteDigital.spec --noconfirm

echo ""
echo " [2/3] Compilando launcher (ExpedienteDigital.exe)..."
echo ""
python.exe -m PyInstaller Launcher.spec --noconfirm

echo ""
echo " [3/3] Empacando distribución..."
echo ""
rm -rf dist/release && mkdir -p dist/release
cp dist/ExpedienteDigital.exe     dist/release/ExpedienteDigital.exe
cp dist/ExpedienteDigital_app.exe dist/release/ExpedienteDigital_app.exe

echo ""
echo " ✔  Listo. Archivos en dist/release/:"
ls -lh dist/release/
echo ""
echo " Para distribuir: zip dist/release/ y compartir."
echo " El usuario descomprime y ejecuta ExpedienteDigital.exe."
