@echo off
REM ── Build completo: launcher + app ─────────────────────────────────────────
REM Ejecutar desde la raíz del proyecto en Windows

echo.
echo  [1/3] Compilando app (ExpedienteDigital_app.exe)...
echo.
python -m PyInstaller ExpedienteDigital.spec --noconfirm
if errorlevel 1 ( echo ERROR compilando app & pause & exit /b 1 )

echo.
echo  [2/3] Compilando launcher (ExpedienteDigital.exe)...
echo.
python -m PyInstaller Launcher.spec --noconfirm
if errorlevel 1 ( echo ERROR compilando launcher & pause & exit /b 1 )

echo.
echo  [3/3] Compilando instalador (ExpedienteDigital_Setup.exe)...
echo.
if not exist dist\installer mkdir dist\installer
iscc installer\ExpedienteDigital.iss
if errorlevel 1 (
  echo.
  echo  NSIS/Inno Setup no encontrado. Instalar desde https://jrsoftware.org/isdl.php
  echo  Luego abrir installer\ExpedienteDigital.iss y compilar con Ctrl+F9.
  echo.
  echo  Los .exe estan en dist\ listos para distribuir como .zip:
  dir dist\ExpedienteDigital.exe dist\ExpedienteDigital_app.exe
)

echo.
echo  ✔  Listo.
echo.
pause
