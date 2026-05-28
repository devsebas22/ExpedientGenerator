@echo off
REM ── Build completo: launcher + app ─────────────────────────────────────────
REM Ejecutar desde la raíz del proyecto en Windows

echo.
echo  [1/3] Compilando app (ExpedienteDigital_app.exe)...
echo.
pyinstaller ExpedienteDigital.spec --noconfirm
if errorlevel 1 ( echo ERROR compilando app & pause & exit /b 1 )

echo.
echo  [2/3] Compilando launcher (ExpedienteDigital.exe)...
echo.
pyinstaller Launcher.spec --noconfirm
if errorlevel 1 ( echo ERROR compilando launcher & pause & exit /b 1 )

echo.
echo  [3/3] Empacando distribucion...
echo.
if exist dist\release rmdir /s /q dist\release
mkdir dist\release
copy /y dist\ExpedienteDigital.exe     dist\release\ExpedienteDigital.exe
copy /y dist\ExpedienteDigital_app.exe dist\release\ExpedienteDigital_app.exe

echo.
echo  ✔  Listo.  Archivos en dist\release\:
dir dist\release
echo.
echo  Para distribuir: comprimir dist\release\ como .zip y compartir.
echo  El usuario descomprime y ejecuta ExpedienteDigital.exe.
echo.
pause
