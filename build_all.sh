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
echo " [3/3] Compilando instalador (ExpedienteDigital_Setup.exe)..."
echo ""
mkdir -p dist/installer
iscc.exe installer/ExpedienteDigital.iss 2>/dev/null || \
  "C:/Program Files (x86)/Inno Setup 6/ISCC.exe" installer/ExpedienteDigital.iss 2>/dev/null || {
    echo " Inno Setup no encontrado."
    echo " Instalar desde https://jrsoftware.org/isdl.php"
    echo " Luego abrir installer/ExpedienteDigital.iss y compilar con Ctrl+F9."
    echo " Los .exe están en dist/ listos para distribuir como .zip."
  }

echo ""
echo " ✔  Listo."
ls -lh dist/installer/ dist/ExpedienteDigital.exe dist/ExpedienteDigital_app.exe 2>/dev/null
