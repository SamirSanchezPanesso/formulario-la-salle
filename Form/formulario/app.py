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


# ============================================================
# Rutas y configuración
# ============================================================

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"

CONFIG = get_config()

logging.basicConfig(
    level=getattr(logging, CONFIG.log_level),
    format="%(asctime)s %(levelname)s %(message)s",
)

LOGGER = logging.getLogger("formulario_lasalle")


# ============================================================
# CORS
# ============================================================

# GitHub Pages usa únicamente el ORIGEN:
# https://samirsanchezpanesso.github.io
#
# No se debe poner:
# https://samirsanchezpanesso.github.io/formulario-la-salle/

DEFAULT_ALLOWED_ORIGINS = {
    "https://samirsanchezpanesso.github.io",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
    "http://localhost:5500",
    "http://127.0.0.1:5500",
}

# Permite añadir más orígenes mediante una variable de entorno:
#
# ALLOWED_ORIGINS=https://ejemplo.com,https://otro-ejemplo.com
extra_origins = {
    origin.strip().rstrip("/")
    for origin in os.getenv("ALLOWED_ORIGINS", "").split(",")
    if origin.strip()
}

ALLOWED_ORIGINS = DEFAULT_ALLOWED_ORIGINS | extra_origins


# ============================================================
# Inicialización de la base de datos
# ============================================================

init_database(CONFIG.database)


# ============================================================
# Servidor HTTP
# ============================================================

class RequestHandler(BaseHTTPRequestHandler):

    # --------------------------------------------------------
    # Logs
    # --------------------------------------------------------

    def log_message(self, format, *args):
        if CONFIG.debug:
            LOGGER.info(
                "%s - %s",
                self.address_string(),
                format % args,
            )

    # --------------------------------------------------------
    # CORS
    # --------------------------------------------------------

    def get_request_origin(self):
        origin = self.headers.get("Origin")

        if not origin:
            return None

        return origin.rstrip("/")

    def is_origin_allowed(self):
        origin = self.get_request_origin()

        # Si no existe Origin, normalmente es una petición
        # directa al servidor, curl, navegador mismo dominio, etc.
        if origin is None:
            return True

        return origin in ALLOWED_ORIGINS

    def add_cors_headers(self):
        origin = self.get_request_origin()

        if origin and origin in ALLOWED_ORIGINS:
            self.send_header(
                "Access-Control-Allow-Origin",
                origin,
            )
            self.send_header(
                "Vary",
                "Origin",
            )

        self.send_header(
            "Access-Control-Allow-Methods",
            "GET, POST, OPTIONS",
        )

        self.send_header(
            "Access-Control-Allow-Headers",
            "Content-Type",
        )

        self.send_header(
            "Access-Control-Max-Age",
            "86400",
        )

    # --------------------------------------------------------
    # Respuestas JSON
    # --------------------------------------------------------

    def send_json(self, status, payload):

        body = json.dumps(
            payload,
            ensure_ascii=False,
        ).encode("utf-8")

        self.send_response(status)

        self.send_header(
            "Content-Type",
            "application/json; charset=utf-8",
        )

        self.send_header(
            "Content-Length",
            str(len(body)),
        )

        self.send_header(
            "Cache-Control",
            "no-store",
        )

        self.add_cors_headers()

        self.end_headers()

        self.wfile.write(body)

    # --------------------------------------------------------
    # Archivos estáticos
    # --------------------------------------------------------

    def send_file(self, file_path):

        file_path = file_path.resolve()

        if not file_path.exists() or not file_path.is_file():
            self.send_error(404)
            return

        content = file_path.read_bytes()

        content_type = (
            mimetypes.guess_type(str(file_path))[0]
            or "application/octet-stream"
        )

        textual_types = {
            "application/javascript",
            "application/json",
            "application/xml",
            "image/svg+xml",
        }

        if (
            content_type.startswith("text/")
            or content_type in textual_types
        ):
            content_type = f"{content_type}; charset=utf-8"

        self.send_response(200)

        self.send_header(
            "Content-Type",
            content_type,
        )

        self.send_header(
            "Content-Length",
            str(len(content)),
        )

        self.send_header(
            "Cache-Control",
            "no-cache",
        )

        self.end_headers()

        self.wfile.write(content)

    # --------------------------------------------------------
    # Preflight CORS
    # --------------------------------------------------------

    def do_OPTIONS(self):

        path = urlparse(self.path).path

        allowed_paths = {
            "/api/contact",
            "/api/environment",
            "/health",
        }

        if path not in allowed_paths:
            self.send_response(404)
            self.send_header("Content-Length", "0")
            self.end_headers()
            return

        if not self.is_origin_allowed():
            self.send_response(403)
            self.send_header("Content-Length", "0")
            self.end_headers()
            return

        self.send_response(204)

        self.add_cors_headers()

        self.send_header(
            "Content-Length",
            "0",
        )

        self.end_headers()

    # --------------------------------------------------------
    # GET
    # --------------------------------------------------------

    def do_GET(self):

        path = urlparse(self.path).path

        # Página principal cuando se accede directamente
        # al servidor Python / Render.
        if path == "/":
            self.send_file(
                STATIC_DIR / "index.html"
            )
            return

        # Devuelve ambiente actual
        if path == "/api/environment":

            if not self.is_origin_allowed():
                self.send_json(
                    403,
                    {
                        "ok": False,
                        "message": "Origen no autorizado.",
                    },
                )
                return

            self.send_json(
                200,
                {
                    "environment": CONFIG.name,
                    "debug": CONFIG.debug,
                },
            )
            return

        # Endpoint para comprobar si Render está activo
        if path == "/health":

            self.send_json(
                200,
                {
                    "status": "ok",
                    "environment": CONFIG.name,
                },
            )
            return

        # Archivos estáticos
        if path.startswith("/static/"):

            relative = path.removeprefix("/static/")

            target = (
                STATIC_DIR / relative
            ).resolve()

            static_root = STATIC_DIR.resolve()

            # Protección contra path traversal
            if (
                target != static_root
                and static_root not in target.parents
            ):
                self.send_error(403)
                return

            self.send_file(target)
            return

        self.send_error(404)

    # --------------------------------------------------------
    # POST
    # --------------------------------------------------------

    def do_POST(self):

        path = urlparse(self.path).path

        if path != "/api/contact":
            self.send_json(
                404,
                {
                    "ok": False,
                    "message": "Ruta no encontrada.",
                },
            )
            return

        # Verificar origen
        if not self.is_origin_allowed():
            self.send_json(
                403,
                {
                    "ok": False,
                    "message": "Origen no autorizado.",
                },
            )
            return

        # ----------------------------------------------------
        # Leer cuerpo de la petición
        # ----------------------------------------------------

        try:
            length = int(
                self.headers.get(
                    "Content-Length",
                    "0",
                )
            )

            if length <= 0:
                self.send_json(
                    400,
                    {
                        "ok": False,
                        "message": "La solicitud está vacía.",
                    },
                )
                return

            # Evita peticiones excesivamente grandes.
            if length > 1_000_000:
                self.send_json(
                    413,
                    {
                        "ok": False,
                        "message": "La solicitud es demasiado grande.",
                    },
                )
                return

            raw_body = self.rfile.read(length)

            data = json.loads(
                raw_body.decode("utf-8")
            )

            if not isinstance(data, dict):
                raise ValueError(
                    "El contenido JSON debe ser un objeto."
                )

        except (
            ValueError,
            json.JSONDecodeError,
            UnicodeDecodeError,
        ):
            self.send_json(
                400,
                {
                    "ok": False,
                    "message": "Solicitud inválida.",
                },
            )
            return

        # ----------------------------------------------------
        # Validaciones
        # ----------------------------------------------------

        errors = validate_contact(data)

        if errors:
            self.send_json(
                422,
                {
                    "ok": False,
                    "message": (
                        "Revisa los campos del formulario."
                    ),
                    "errors": errors,
                },
            )
            return

        # ----------------------------------------------------
        # Guardar en base de datos
        # ----------------------------------------------------

        try:

            record_id = save_contact(
                CONFIG.database,
                data,
                CONFIG.name,
            )

        except Exception:
            LOGGER.exception(
                "No fue posible almacenar el contacto."
            )

            self.send_json(
                500,
                {
                    "ok": False,
                    "message": (
                        "Ocurrió un error al guardar el mensaje."
                    ),
                },
            )
            return

        if CONFIG.debug:
            LOGGER.debug(
                "Contacto almacenado con id %s en %s",
                record_id,
                CONFIG.database.name,
            )

        self.send_json(
            201,
            {
                "ok": True,
                "message": (
                    "Tu mensaje fue enviado correctamente."
                ),
                "id": record_id,
            },
        )


# ============================================================
# Crear servidor
# ============================================================

def create_server(host=None, port=None):

    resolved_host = (
        host
        or os.getenv(
            "HOST",
            "127.0.0.1",
        )
    )

    resolved_port = int(
        port
        or os.getenv(
            "PORT",
            "8000",
        )
    )

    return ThreadingHTTPServer(
        (
            resolved_host,
            resolved_port,
        ),
        RequestHandler,
    )


# ============================================================
# Ejecutar
# ============================================================

def main():

    server = create_server()

    LOGGER.warning(
        (
            "Formulario La Salle ejecutándose "
            "en http://%s:%s con ambiente %s"
        ),
        server.server_address[0],
        server.server_address[1],
        CONFIG.name,
    )

    LOGGER.warning(
        "Orígenes CORS permitidos: %s",
        ", ".join(
            sorted(ALLOWED_ORIGINS)
        ),
    )

    try:
        server.serve_forever()

    except KeyboardInterrupt:
        LOGGER.warning(
            "Servidor detenido manualmente."
        )

    finally:
        server.server_close()


if __name__ == "__main__":
    main()
