@echo off
rem Ejecutar desde cualquier carpeta, incluso con doble clic.
setlocal
cd /d "%~dp0"
set "APP_ENV=production"
set "HOST=0.0.0.0"
if not defined PORT set "PORT=8002"
python app.py
if errorlevel 1 pause
endlocal
