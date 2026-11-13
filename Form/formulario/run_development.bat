@echo off
rem Ejecutar desde cualquier carpeta, incluso con doble clic.
setlocal
cd /d "%~dp0"
set "APP_ENV=development"
set "HOST=127.0.0.1"
if not defined PORT set "PORT=8000"
python app.py
if errorlevel 1 pause
endlocal
