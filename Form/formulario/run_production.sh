#!/usr/bin/env sh
# Ejecutar desde cualquier directorio. El intérprete puede cambiarse con PYTHON.
set -eu
cd -- "$(dirname -- "$0")"
export APP_ENV=production
export HOST=0.0.0.0
export PORT="${PORT:-8002}"
exec "${PYTHON:-python3}" app.py
