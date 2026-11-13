"""Servidor del prototipo académico La Salle con Python estándar y SQLite.

Se conserva la arquitectura original para facilitar el despliegue en Render.
Este servidor sirve la demostración académica; no implementa un servicio de
correo ni una consola administrativa de atención institucional.
"""

import json
import logging
import mimetypes
import os
import socket
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlsplit

from config import get_config
from storage import init_database, save_contact
from validators import validate_contact

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
CONFIG = get_config()
MAX_BODY_BYTES = 32 * 1024
REQUEST_TIMEOUT_SECONDS = 10

logging.basicConfig(
    level=getattr(logging, CONFIG.log_level),
    format="%(asctime)s %(levelname)s %(message)s",
)
LOGGER = logging.getLogger("formulario_lasalle")

DEFAULT_ALLOWED_ORIGINS = {
    "https://samirsanchezpanesso.github.io",
    "https://formulario-la-salle.onrender.com",
    "http://localhost:8000", "http://127.0.0.1:8000",
    "http://localhost:5500", "http://127.0.0.1:5500",
}


def read_allowed_origins():
    """Admite orígenes completos: esquema y dominio, sin rutas ni comodines."""
    origenes = set(DEFAULT_ALLOWED_ORIGINS)
    for valor in os.getenv("ALLOWED_ORIGINS", "").split(","):
        origen = valor.strip().rstrip("/")
        if not origen:
            continue
        partes = urlsplit(origen)
        if (
            partes.scheme not in {"http", "https"} or not partes.netloc
            or partes.username is not None or partes.password is not None
            or partes.path or partes.query or partes.fragment or "*" in origen
        ):
            raise ValueError(
                "ALLOWED_ORIGINS debe contener orígenes como "
                "https://usuario.github.io, separados por comas y sin rutas."
            )
        origenes.add(origen)
    return origenes


ALLOWED_ORIGINS = read_allowed_origins()
init_database(CONFIG.database)


class RequestHandler(BaseHTTPRequestHandler):
    server_version = "FormularioLaSalle/2.0"
    sys_version = ""

    def setup(self):
        super().setup()
        # Una conexión que deja de enviar datos no bloquea indefinidamente
        # el hilo de atención. Render puede usar su propio tiempo de espera.
        self.connection.settimeout(REQUEST_TIMEOUT_SECONDS)

    def log_message(self, format, *args):
        if CONFIG.debug:
            LOGGER.info("%s", format % args)

    def get_request_origin(self):
        return self.headers.get("Origin")

    def is_origin_allowed(self):
        origen = self.get_request_origin()
        if origen is None:
            return True
        if origen in ALLOWED_ORIGINS:
            return True
        # La página y la API pueden compartir el mismo dominio de Render.
        # No hace falta añadir ese dominio dinámico a los orígenes externos.
        host = self.headers.get("Host", "")
        return bool(host) and origen in {f"http://{host}", f"https://{host}"}

    def add_cors_headers(self):
        origen = self.get_request_origin()
        self.send_header("Vary", "Origin")
        if origen and self.is_origin_allowed():
            self.send_header("Access-Control-Allow-Origin", origen)
        # No se permiten credenciales ni orígenes con '*'.
        self.send_header("Access-Control-Allow-Methods", "GET, HEAD, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Max-Age", "600")

    def add_security_headers(self):
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "strict-origin-when-cross-origin")

    def write_body(self, cuerpo):
        if self.command == "HEAD":
            return
        try:
            self.wfile.write(cuerpo)
        except (BrokenPipeError, ConnectionResetError, socket.timeout):
            # El visitante puede cerrar la pestaña durante la respuesta.
            pass

    def send_json(self, status, payload):
        cuerpo = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(cuerpo)))
        self.send_header("Cache-Control", "no-store")
        self.add_security_headers()
        self.add_cors_headers()
        self.end_headers()
        self.write_body(cuerpo)

    def send_file(self, file_path):
        # Resolver symlinks y '..' antes de leer impide salir de static.
        raiz = STATIC_DIR.resolve()
        destino = Path(file_path).resolve()
        if destino == raiz or not destino.is_relative_to(raiz):
            self.send_json(403, {"ok": False, "message": "Ruta no permitida."})
            return
        relativos = destino.relative_to(raiz).parts
        if any(parte.startswith(".") for parte in relativos):
            self.send_json(404, {"ok": False, "message": "Archivo no encontrado."})
            return
        if not destino.is_file():
            self.send_json(404, {"ok": False, "message": "Archivo no encontrado."})
            return
        try:
            cuerpo = destino.read_bytes()
        except OSError:
            self.send_json(500, {"ok": False, "message": "No se pudo leer el archivo."})
            return
        tipo = mimetypes.guess_type(str(destino))[0] or "application/octet-stream"
        if tipo.startswith("text/") or tipo in {
            "application/javascript", "application/json", "image/svg+xml"
        }:
            tipo += "; charset=utf-8"
        self.send_response(200)
        self.send_header("Content-Type", tipo)
        self.send_header("Content-Length", str(len(cuerpo)))
        self.send_header("Cache-Control", "no-cache")
        self.add_security_headers()
        self.end_headers()
        self.write_body(cuerpo)

    def do_OPTIONS(self):
        ruta = urlsplit(self.path).path
        if ruta not in {"/api/contact", "/api/environment", "/health"}:
            self.send_json(404, {"ok": False, "message": "Ruta no encontrada."})
            return
        if not self.is_origin_allowed():
            self.send_json(403, {"ok": False, "message": "Origen no autorizado."})
            return
        metodo = self.headers.get("Access-Control-Request-Method", "POST").upper()
        cabeceras = {
            valor.strip().lower()
            for valor in self.headers.get("Access-Control-Request-Headers", "").split(",")
            if valor.strip()
        }
        if metodo not in {"GET", "HEAD", "POST"} or not cabeceras <= {"content-type"}:
            self.send_json(403, {"ok": False, "message": "Preconsulta no permitida."})
            return
        self.send_response(204)
        self.add_cors_headers()
        self.add_security_headers()
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_HEAD(self):
        self.do_GET()

    def do_GET(self):
        ruta = unquote(urlsplit(self.path).path)
        if "\x00" in ruta or "\\" in ruta:
            self.send_json(400, {"ok": False, "message": "Ruta inválida."})
            return
        if ruta in {"/api/environment", "/health"}:
            if not self.is_origin_allowed():
                self.send_json(403, {"ok": False, "message": "Origen no autorizado."})
                return
            if ruta == "/api/environment":
                self.send_json(200, {"environment": CONFIG.name, "debug": CONFIG.debug})
            else:
                self.send_json(200, {"status": "ok", "environment": CONFIG.name})
            return
        if ruta.startswith("/api/"):
            self.send_json(404, {"ok": False, "message": "Ruta no encontrada."})
            return

        # Estos alias permiten usar el mismo HTML de Pages en la raíz Render:
        # /styles.css, /app.js, /config.js, /assets/... y /static/... (anterior).
        relativo = ruta.removeprefix("/static/") if ruta.startswith("/static/") else ruta.lstrip("/")
        if relativo in {"", "static/"}:
            relativo = "index.html"
        self.send_file(STATIC_DIR / relativo)

    def do_POST(self):
        if urlsplit(self.path).path != "/api/contact":
            self.send_json(404, {"ok": False, "message": "Ruta no encontrada."})
            return
        if not self.is_origin_allowed():
            self.send_json(403, {"ok": False, "message": "Origen no autorizado."})
            return
        if self.headers.get("Transfer-Encoding"):
            self.send_json(400, {"ok": False, "message": "Usa Content-Length para enviar JSON."})
            return
        tipo = self.headers.get("Content-Type", "").split(";", 1)[0].strip().lower()
        if tipo != "application/json":
            self.send_json(415, {"ok": False, "message": "Envía el contenido como application/json."})
            return
        longitudes = self.headers.get_all("Content-Length", [])
        if not longitudes:
            self.send_json(411, {"ok": False, "message": "Falta Content-Length en la solicitud."})
            return
        try:
            if len(longitudes) != 1:
                raise ValueError
            longitud = int(longitudes[0])
            if longitud <= 0:
                raise ValueError
        except (TypeError, ValueError):
            self.send_json(400, {"ok": False, "message": "La longitud de la solicitud no es válida."})
            return
        if longitud > MAX_BODY_BYTES:
            self.send_json(413, {"ok": False, "message": "La solicitud supera el límite de 32 KiB."})
            return
        try:
            cuerpo = self.rfile.read(longitud)
            if len(cuerpo) != longitud:
                raise ValueError
            datos = json.loads(cuerpo.decode("utf-8"))
            if not isinstance(datos, dict):
                raise ValueError
        except socket.timeout:
            self.send_json(408, {"ok": False, "message": "Se agotó el tiempo de recepción. Inténtalo nuevamente."})
            return
        except (ValueError, UnicodeDecodeError):
            self.send_json(400, {"ok": False, "message": "La solicitud debe contener un objeto JSON válido."})
            return

        errores = validate_contact(datos)
        if errores:
            self.send_json(422, {"ok": False, "message": "Revisa los campos del formulario.", "errors": errores})
            return
        try:
            identificador = save_contact(CONFIG.database, datos, CONFIG.name)
        except Exception:
            # La respuesta no revela datos personales ni rutas internas.
            LOGGER.exception("No fue posible almacenar el contacto.")
            self.send_json(500, {"ok": False, "message": "No se pudo registrar el mensaje. Conserva tus datos e inténtalo nuevamente."})
            return
        self.send_json(201, {"ok": True, "message": "Mensaje registrado correctamente.", "id": identificador})


def create_server(host=None, port=None):
    """Conserva la interfaz original y acepta port=0 para pruebas aisladas."""
    servidor_host = host if host is not None else os.getenv("HOST", "127.0.0.1")
    puertos = {"development": 8000, "testing": 8001, "production": 8002}
    servidor_puerto = int(port if port is not None else os.getenv("PORT", str(puertos[CONFIG.name])))
    if not 0 <= servidor_puerto <= 65535:
        raise ValueError("PORT debe ser un entero entre 0 y 65535.")
    return ThreadingHTTPServer((servidor_host, servidor_puerto), RequestHandler)


def main():
    servidor = create_server()
    LOGGER.warning(
        "Formulario La Salle: http://%s:%s - ambiente %s",
        servidor.server_address[0], servidor.server_address[1], CONFIG.name,
    )
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        LOGGER.warning("Servidor detenido.")
    finally:
        servidor.server_close()


if __name__ == "__main__":
    main()
