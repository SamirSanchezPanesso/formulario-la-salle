"""Servidor local exclusivo de la suite funcional con CORS del puerto efímero."""
import json
import os
import sys
from pathlib import Path
os.environ['APP_ENV'] = 'testing'
os.environ['PORT'] = '0'
sys.path.insert(0, str(Path(sys.argv[1]).resolve()))
import app
server = app.create_server('127.0.0.1', 0)
base = f'http://127.0.0.1:{server.server_address[1]}'
app.ALLOWED_ORIGINS.add(base)
print(json.dumps({'base_url': base, 'database': str(app.CONFIG.database),
                  'environment': app.CONFIG.name, 'additional_allowed_origin': base}), flush=True)
try:
    server.serve_forever()
finally:
    server.server_close()
