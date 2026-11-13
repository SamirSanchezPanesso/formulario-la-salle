@echo off
rem Ejecutar desde cualquier carpeta, incluso con doble clic.
setlocal
cd /d "%~dp0"
set "APP_ENV=testing"
set "HOST=127.0.0.1"
if not defined PORT set "PORT=8001"
python app.py
if errorlevel 1 pause
endlocal
