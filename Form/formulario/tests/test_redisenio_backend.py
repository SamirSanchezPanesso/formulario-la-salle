"""Pruebas locales del rediseño: HTTP real y SQLite en un directorio temporal.

Ejecución desde Form/formulario:
    python -m unittest discover -s tests -p "test_redisenio_backend.py" -v

No se contacta Render, no se envía correo ni se abre una base con datos reales.
Los archivos estáticos de prueba son temporales y no modifican la interfaz.
"""

import http.client
import json
import os
import sqlite3
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

RAIZ = Path(__file__).resolve().parents[1]
TEMPORAL = tempfile.TemporaryDirectory(prefix="lasalle_backend_")
CARPETA = Path(TEMPORAL.name)
ENTORNO_ANTERIOR = {clave: os.environ.get(clave) for clave in ("APP_ENV", "DATABASE_PATH")}
os.environ["APP_ENV"] = "testing"
os.environ["DATABASE_PATH"] = str(CARPETA / "contacts_testing.db")
sys.path.insert(0, str(RAIZ))

import app
import config
from storage import init_database
from validators import validate_contact

VALIDO = {
    "name": "  Ana Torres  ",
    "email": "  ana@example.com  ",
    "subject": "  Consulta académica  ",
    "message": "  Quisiera conocer más información del programa.  ",
}


def tearDownModule():
    TEMPORAL.cleanup()
    for clave, valor in ENTORNO_ANTERIOR.items():
        if valor is None:
            os.environ.pop(clave, None)
        else:
            os.environ[clave] = valor


class BackendRedisenioTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.raiz_estatica_original = app.STATIC_DIR
        app.STATIC_DIR = CARPETA / "static"
        app.STATIC_DIR.mkdir()
        (app.STATIC_DIR / "assets").mkdir()
        archivos = {
            "index.html": "<!doctype html><html lang='es'><title>Prueba</title></html>",
            "styles.css": "body { color: #123; }",
            "app.js": "console.log('prueba');",
            "config.js": "window.CONFIG = {};",
            "assets/icon.svg": "<svg xmlns='http://www.w3.org/2000/svg'></svg>",
            ".env": "NO_PUBLICAR=secreto",
        }
        for relativo, contenido in archivos.items():
            (app.STATIC_DIR / relativo).write_text(contenido, encoding="utf-8")
        (CARPETA / "secret.txt").write_text("NO_PUBLICAR", encoding="utf-8")
        cls.servidor = app.create_server("127.0.0.1", 0)
        cls.puerto = cls.servidor.server_address[1]
        cls.hilo = threading.Thread(target=cls.servidor.serve_forever, daemon=True)
        cls.hilo.start()
        app.LOGGER.disabled = True

    @classmethod
    def tearDownClass(cls):
        cls.servidor.shutdown()
        cls.servidor.server_close()
        cls.hilo.join(timeout=3)
        app.STATIC_DIR = cls.raiz_estatica_original
        app.LOGGER.disabled = False

    def setUp(self):
        with sqlite3.connect(app.CONFIG.database) as conexion:
            conexion.execute("DELETE FROM contacts")

    def filas(self):
        with sqlite3.connect(app.CONFIG.database) as conexion:
            conexion.row_factory = sqlite3.Row
            return [dict(fila) for fila in conexion.execute("SELECT * FROM contacts")]

    def solicitar(self, metodo="GET", ruta="/health", datos=None, cabeceras=None, cuerpo=None):
        cabeceras = dict(cabeceras or {})
        if datos is not None:
            cuerpo = json.dumps(datos).encode("utf-8")
            cabeceras.setdefault("Content-Type", "application/json")
        conexion = http.client.HTTPConnection("127.0.0.1", self.puerto, timeout=3)
        try:
            conexion.request(metodo, ruta, body=cuerpo, headers=cabeceras)
            respuesta = conexion.getresponse()
            contenido = respuesta.read()
            tipo = respuesta.getheader("Content-Type", "")
            if contenido and "application/json" in tipo:
                contenido = json.loads(contenido)
            return respuesta.status, dict(respuesta.getheaders()), contenido
        finally:
            conexion.close()

    def test_01_envio_valido_guarda_y_confirma(self):
        estado, _, cuerpo = self.solicitar("POST", "/api/contact", datos=VALIDO)
        self.assertEqual(estado, 201)
        self.assertEqual(cuerpo["message"], "Mensaje registrado correctamente.")
        self.assertTrue(cuerpo["ok"])
        filas = self.filas()
        self.assertEqual(len(filas), 1)
        self.assertEqual(cuerpo["id"], filas[0]["id"])
        for campo, valor in VALIDO.items():
            self.assertEqual(filas[0][campo], valor.strip())
        self.assertEqual(filas[0]["environment"], "testing")

    def test_02_obligatorios_sin_insercion(self):
        estado, _, cuerpo = self.solicitar("POST", "/api/contact", datos={})
        self.assertEqual(estado, 422)
        self.assertEqual(set(cuerpo["errors"]), set(VALIDO))
        self.assertEqual(self.filas(), [])

    def test_03_tipos_invalidos_sin_error_500(self):
        for valor in (None, 12, True, [], {}):
            with self.subTest(valor=valor):
                datos = {**VALIDO, "name": valor}
                estado, _, cuerpo = self.solicitar("POST", "/api/contact", datos=datos)
                self.assertEqual(estado, 422)
                self.assertIn("name", cuerpo["errors"])
        self.assertEqual(self.filas(), [])

    def test_04_limites_texto(self):
        for campo, minimo, maximo in (("name", 2, 100), ("subject", 3, 120), ("message", 10, 2000)):
            for cantidad in (minimo, maximo):
                with self.subTest(campo=campo, cantidad=cantidad):
                    self.assertNotIn(campo, validate_contact({**VALIDO, campo: "x" * cantidad}))
            for cantidad in (minimo - 1, maximo + 1):
                with self.subTest(campo=campo, cantidad=cantidad):
                    self.assertIn(campo, validate_contact({**VALIDO, campo: "x" * cantidad}))

    def test_05_correo_formato_y_limite(self):
        for correo in ("incorrecto", "nombre@", "a..b@example.com", ".ana@example.com", "ana@-dominio.com"):
            with self.subTest(correo=correo):
                self.assertIn("email", validate_contact({**VALIDO, "email": correo}))
        largo_valido = "a" * 64 + "@" + "b" * 63 + "." + "c" * 63 + "." + "d" * 61
        self.assertEqual(len(largo_valido), 254)
        self.assertNotIn("email", validate_contact({**VALIDO, "email": largo_valido}))
        self.assertIn("email", validate_contact({**VALIDO, "email": largo_valido + "e"}))

    def test_06_validacion_no_modifica_datos(self):
        datos = dict(VALIDO)
        self.assertEqual(validate_contact(datos), {})
        self.assertEqual(datos, VALIDO)

    def test_07_json_malformado_y_no_objeto(self):
        for cuerpo in (b"{", b"[]", b"null", b'"texto"', b"\xff"):
            with self.subTest(cuerpo=cuerpo):
                estado, _, _ = self.solicitar("POST", "/api/contact", cuerpo=cuerpo, cabeceras={"Content-Type": "application/json"})
                self.assertEqual(estado, 400)
        self.assertEqual(self.filas(), [])

    def test_08_tipo_de_contenido(self):
        estado, _, _ = self.solicitar("POST", "/api/contact", cuerpo=b"hola", cabeceras={"Content-Type": "text/plain"})
        self.assertEqual(estado, 415)

    def test_09_cuerpo_excesivo(self):
        estado, _, _ = self.solicitar("POST", "/api/contact", cuerpo=b"x" * (app.MAX_BODY_BYTES + 1), cabeceras={"Content-Type": "application/json"})
        self.assertEqual(estado, 413)
        self.assertEqual(self.filas(), [])

    def test_10_longitud_ausente_y_duplicada(self):
        for longitudes, esperado in (([], 411), (["-1"], 400), (["2", "2"], 400), (["texto"], 400)):
            with self.subTest(longitudes=longitudes):
                conexion = http.client.HTTPConnection("127.0.0.1", self.puerto, timeout=3)
                try:
                    conexion.putrequest("POST", "/api/contact")
                    conexion.putheader("Content-Type", "application/json")
                    for longitud in longitudes:
                        conexion.putheader("Content-Length", longitud)
                    conexion.endheaders()
                    respuesta = conexion.getresponse()
                    self.assertEqual(respuesta.status, esperado)
                    respuesta.read()
                finally:
                    conexion.close()

    def test_11_estaticos_raiz_y_ruta_anterior(self):
        for recurso in ("index.html", "styles.css", "app.js", "config.js", "assets/icon.svg"):
            with self.subTest(recurso=recurso):
                estado, _, contenido = self.solicitar(ruta="/" + recurso)
                estado_anterior, _, contenido_anterior = self.solicitar(ruta="/static/" + recurso)
                self.assertEqual(estado, 200)
                self.assertEqual(estado_anterior, 200)
                self.assertEqual(contenido, contenido_anterior)
        self.assertEqual(self.solicitar(ruta="/")[0], 200)

    def test_12_traversal_y_archivos_privados(self):
        for ruta in ("/static/../secret.txt", "/static/%2e%2e/secret.txt", "/%2e%2e/secret.txt"):
            with self.subTest(ruta=ruta):
                estado, _, contenido = self.solicitar(ruta=ruta)
                self.assertEqual(estado, 403)
                self.assertNotIn("NO_PUBLICAR", str(contenido))
        for ruta in ("/.env", "/app.py", "/data/contacts_testing.db"):
            with self.subTest(ruta=ruta):
                self.assertEqual(self.solicitar(ruta=ruta)[0], 404)

    def test_13_symlink_fuera_de_static(self):
        enlace = app.STATIC_DIR / "atajo.txt"
        try:
            enlace.symlink_to(CARPETA / "secret.txt")
        except (NotImplementedError, OSError):
            self.skipTest("Este sistema no permite crear enlaces simbólicos.")
        try:
            self.assertEqual(self.solicitar(ruta="/atajo.txt")[0], 403)
        finally:
            enlace.unlink()

    def test_14_cors_origen_exacto(self):
        origen = "https://samirsanchezpanesso.github.io"
        estado, cabeceras, _ = self.solicitar("OPTIONS", "/api/contact", cabeceras={"Origin": origen, "Access-Control-Request-Method": "POST", "Access-Control-Request-Headers": "Content-Type"})
        self.assertEqual(estado, 204)
        self.assertEqual(cabeceras.get("Access-Control-Allow-Origin"), origen)
        self.assertNotIn("Access-Control-Allow-Credentials", cabeceras)
        for origen_malo in (origen + ".intruso.example", "null"):
            estado, cabeceras, _ = self.solicitar("POST", "/api/contact", datos=VALIDO, cabeceras={"Origin": origen_malo})
            self.assertEqual(estado, 403)
            self.assertNotIn("Access-Control-Allow-Origin", cabeceras)
        self.assertEqual(self.filas(), [])

    def test_15_mismo_origen_y_preconsulta_limitada(self):
        origen = f"http://127.0.0.1:{self.puerto}"
        self.assertEqual(self.solicitar("POST", "/api/contact", datos=VALIDO, cabeceras={"Origin": origen})[0], 201)
        self.assertEqual(self.solicitar("OPTIONS", "/api/contact", cabeceras={"Origin": origen, "Access-Control-Request-Method": "DELETE"})[0], 403)

    def test_16_salud_y_head(self):
        estado, cabeceras, cuerpo = self.solicitar()
        self.assertEqual(estado, 200)
        self.assertEqual(cuerpo, {"status": "ok", "environment": "testing"})
        self.assertEqual(cabeceras["X-Content-Type-Options"], "nosniff")
        estado, cabeceras, cuerpo = self.solicitar("HEAD", "/styles.css")
        self.assertEqual(estado, 200)
        self.assertGreater(int(cabeceras["Content-Length"]), 0)
        self.assertEqual(cuerpo, b"")

    def test_17_fallo_almacenamiento_no_confirma(self):
        with patch.object(app, "save_contact", side_effect=sqlite3.OperationalError("simulado")):
            estado, _, cuerpo = self.solicitar("POST", "/api/contact", datos=VALIDO)
        self.assertEqual(estado, 500)
        self.assertFalse(cuerpo["ok"])
        self.assertNotIn("id", cuerpo)
        self.assertNotIn("simulado", cuerpo["message"])
        self.assertEqual(self.filas(), [])

    def test_18_configuracion_rechaza_ambiente_desconocido(self):
        with patch.dict(os.environ, {"APP_ENV": "producion"}):
            with self.assertRaises(ValueError):
                config.get_config()
        with patch.dict(os.environ, {"APP_ENV": "production", "DATABASE_PATH": ""}):
            resultado = config.get_config()
            self.assertFalse(resultado.debug)
            self.assertEqual(resultado.database.name, "contacts_production.db")

    def test_19_ruta_base_configurable(self):
        with patch.dict(os.environ, {"APP_ENV": "testing", "DATABASE_PATH": "datos_nuevos/contactos.db"}):
            self.assertEqual(config.get_config().database, (RAIZ / "datos_nuevos/contactos.db").resolve())

    def test_20_base_existente_se_conserva(self):
        self.solicitar("POST", "/api/contact", datos=VALIDO)
        antes = self.filas()
        self.assertEqual(len(antes), 1)
        init_database(app.CONFIG.database)
        self.assertEqual(self.filas(), antes)

    def test_21_configuracion_cors_rechaza_rutas(self):
        for origen in ("*", "https://usuario.github.io/proyecto", "https://usuario:clave@example.com"):
            with self.subTest(origen=origen), patch.dict(os.environ, {"ALLOWED_ORIGINS": origen}):
                with self.assertRaises(ValueError):
                    app.read_allowed_origins()

    def test_22_texto_sql_se_guarda_como_texto(self):
        texto = "Consulta '); DROP TABLE contacts; --"
        estado, _, _ = self.solicitar("POST", "/api/contact", datos={**VALIDO, "message": texto})
        self.assertEqual(estado, 201)
        self.assertEqual(self.filas()[0]["message"], texto)


if __name__ == "__main__":
    unittest.main(verbosity=2)
