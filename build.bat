@echo off
REM ── Build de Expediente Digital para Windows ────────────────────────────────
REM Requisitos: pip install pyinstaller requests
REM Ejecutar desde la raíz del proyecto

echo.
echo  Compilando Expediente Digital...
echo.

pyinstaller ^
  --onefile ^
  --windowed ^
  --name "ExpedienteDigital" ^
  --add-data "frontend;frontend" ^
  --hidden-import "backend.main" ^
  --hidden-import "backend.models" ^
  --hidden-import "backend.pdf_processor" ^
  --hidden-import "backend.session_manager" ^
  run.py

echo.
echo  ✅  Listo. El .exe está en dist\ExpedienteDigital.exe
echo.
pause
