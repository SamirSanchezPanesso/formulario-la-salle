#!/usr/bin/env sh
# Ejecutar desde cualquier directorio. El intérprete puede cambiarse con PYTHON.
set -eu
cd -- "$(dirname -- "$0")"
export APP_ENV=testing
export HOST=127.0.0.1
export PORT="${PORT:-8001}"
exec "${PYTHON:-python3}" app.py
