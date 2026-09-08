import json
import os
import sys
import threading
import unittest
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ["APP_ENV"] = "testing"
from app import create_server

class FormularioContactoTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = create_server("127.0.0.1", 0)
        cls.port = cls.server.server_address[1]
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def post(self, payload):
        data = json.dumps(payload).encode("utf-8")
        request = Request(
            f"http://127.0.0.1:{self.port}/api/contact",
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        try:
            response = urlopen(request)
            return response.status, json.loads(response.read().decode("utf-8"))
        except HTTPError as error:
            return error.code, json.loads(error.read().decode("utf-8"))

    def test_envio_correcto(self):
        status, body = self.post({"name": "Ana Torres", "email": "ana@example.com", "subject": "Información", "message": "Solicito información del programa."})
        self.assertEqual(status, 201)
        self.assertTrue(body["ok"])
        self.assertEqual(body["message"], "Tu mensaje fue enviado correctamente.")

    def test_campo_obligatorio_vacio(self):
        status, body = self.post({"name": "", "email": "ana@example.com", "subject": "Información", "message": "Mensaje"})
        self.assertEqual(status, 422)
        self.assertIn("name", body["errors"])

    def test_correo_invalido(self):
        status, body = self.post({"name": "Ana Torres", "email": "correo-invalido", "subject": "Información", "message": "Mensaje"})
        self.assertEqual(status, 422)
        self.assertIn("email", body["errors"])

if __name__ == "__main__":
    unittest.main(verbosity=2)
