import json
import logging
import mimetypes
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse
from config import get_config
from storage import init_database, save_contact
from validators import validate_contact

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
CONFIG = get_config()
logging.basicConfig(level=getattr(logging, CONFIG.log_level), format="%(asctime)s %(levelname)s %(message)s")
LOGGER = logging.getLogger("formulario_lasalle")
init_database(CONFIG.database)

class RequestHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        if CONFIG.debug:
            LOGGER.info("%s - %s", self.address_string(), format % args)

    def send_json(self, status, payload):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def send_file(self, file_path):
        if not file_path.exists() or not file_path.is_file():
            self.send_error(404)
            return
        content = file_path.read_bytes()
        content_type = mimetypes.guess_type(str(file_path))[0] or "application/octet-stream"
        self.send_response(200)
        self.send_header("Content-Type", f"{content_type}; charset=utf-8" if content_type.startswith("text/") else content_type)
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/":
            self.send_file(STATIC_DIR / "index.html")
            return
        if path == "/api/environment":
            self.send_json(200, {"environment": CONFIG.name, "debug": CONFIG.debug})
            return
        if path == "/health":
            self.send_json(200, {"status": "ok", "environment": CONFIG.name})
            return
        if path.startswith("/static/"):
            relative = path.removeprefix("/static/")
            target = (STATIC_DIR / relative).resolve()
            if STATIC_DIR.resolve() not in target.parents:
                self.send_error(403)
                return
            self.send_file(target)
            return
        self.send_error(404)

    def do_POST(self):
        path = urlparse(self.path).path
        if path != "/api/contact":
            self.send_error(404)
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            data = json.loads(self.rfile.read(length).decode("utf-8"))
        except (ValueError, json.JSONDecodeError, UnicodeDecodeError):
            self.send_json(400, {"ok": False, "message": "Solicitud inválida."})
            return
        errors = validate_contact(data)
        if errors:
            self.send_json(422, {"ok": False, "message": "Revisa los campos del formulario.", "errors": errors})
            return
        record_id = save_contact(CONFIG.database, data, CONFIG.name)
        if CONFIG.debug:
            LOGGER.debug("Contacto almacenado con id %s en %s", record_id, CONFIG.database.name)
        self.send_json(201, {"ok": True, "message": "Tu mensaje fue enviado correctamente.", "id": record_id})

def create_server(host=None, port=None):
    resolved_host = host or os.getenv("HOST", "127.0.0.1")
    resolved_port = int(port or os.getenv("PORT", "8000"))
    return ThreadingHTTPServer((resolved_host, resolved_port), RequestHandler)

def main():
    server = create_server()
    LOGGER.warning("Formulario La Salle ejecutándose en http://%s:%s con ambiente %s", server.server_address[0], server.server_address[1], CONFIG.name)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()

if __name__ == "__main__":
    main()
