"""Cuatro casos U/I sobre la aplicación original o su copia corregida."""
import argparse
import json
import os
import platform
import sqlite3
import sys
import threading
import time
import traceback
import unittest
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

PARSER = argparse.ArgumentParser()
PARSER.add_argument('--app', required=True)
PARSER.add_argument('--output', required=True)
PARSER.add_argument('--variant', required=True)
ARGS = PARSER.parse_args()
APP = Path(ARGS.app).resolve()
OUTPUT = Path(ARGS.output).resolve()
OUTPUT.mkdir(parents=True, exist_ok=True)
os.environ['APP_ENV'] = 'testing'
os.environ['PORT'] = '0'
sys.path.insert(0, str(APP))
import app
from validators import validate_contact

VALID = {'name': '  Ana Prueba  ', 'email': '  ana.prueba@example.com  ',
         'subject': '  Consulta académica  ',
         'message': '  Solicito información del programa.  '}
INVALID = {key: value.strip() for key, value in VALID.items()}
INVALID['name'] = None


def utc_now():
    return datetime.now(timezone.utc).isoformat()


class SixCaseBackend(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = app.create_server('127.0.0.1', 0)
        cls.base = f'http://127.0.0.1:{cls.server.server_address[1]}'
        app.ALLOWED_ORIGINS.add(cls.base)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=3)

    def setUp(self):
        with sqlite3.connect(app.CONFIG.database) as db:
            db.execute('DELETE FROM contacts')
            db.execute("DELETE FROM sqlite_sequence WHERE name='contacts'")
        self.started = utc_now()
        self.start_timer = time.perf_counter()
        self.record = None

    def tearDown(self):
        if self.record is not None:
            self.record.update({
                'started_at_utc': self.started,
                'finished_at_utc': utc_now(),
                'duration_seconds': round(time.perf_counter() - self.start_timer, 6),
                'variant': ARGS.variant,
                'execution': 'real local execution',
                'environment': {'APP_ENV': 'testing', 'base_url': self.base,
                    'database_scope': 'temporary copy of the application',
                    'additional_allowed_origin': self.base,
                    'python_version': platform.python_version()},
            })
            (OUTPUT / (self.record['id'] + '.json')).write_text(
                json.dumps(self.record, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
            print('EVIDENCE ' + json.dumps(self.record, ensure_ascii=False), flush=True)

    def case(self, id_, name, inputs, expected, observed, checks):
        self.record = {'id': id_, 'name': name, 'inputs': inputs,
            'expected': expected, 'observed': observed,
            'actual_assertions': [dict(label=label, passed=bool(ok)) for label, ok in checks],
            'status': 'APROBADO' if all(ok for _, ok in checks) else 'FALLIDO'}
        for label, ok in checks:
            self.assertTrue(ok, label)

    def rows(self):
        with sqlite3.connect(app.CONFIG.database) as db:
            db.row_factory = sqlite3.Row
            return [dict(row) for row in db.execute('SELECT * FROM contacts ORDER BY id')]

    def post(self, data):
        request = Request(self.base + '/api/contact',
            data=json.dumps(data).encode('utf-8'),
            headers={'Content-Type': 'application/json', 'Origin': self.base}, method='POST')
        try:
            response = urlopen(request, timeout=5)
        except HTTPError as error:
            response = error
        with response:
            return {'status': response.status,
                    'headers': dict(response.headers.items()),
                    'body': json.loads(response.read().decode('utf-8'))}

    def test_U01_valid_text(self):
        payload = dict(VALID)
        result = validate_contact(payload)
        self.case('U01', 'Campos de texto válidos con espacios externos', payload,
            {'errors': {}}, {'errors': result, 'input_unchanged': payload == VALID},
            [('validate_contact devuelve un diccionario vacío', result == {}),
             ('La validación no altera la entrada', payload == VALID)])

    def test_U02_null_name(self):
        result = validate_contact(dict(INVALID))
        self.case('U02', 'Rechazo de nombre nulo', INVALID,
            {'errors_contains': 'name', 'message': 'Este campo debe ser texto.'},
            {'errors': result},
            [('El valor null produce un error para name', 'name' in result)])

    def test_I01_persistence(self):
        before = self.rows()
        response = self.post(dict(VALID))
        after = self.rows()
        expected_text = {key: value.strip() for key, value in VALID.items()}
        persisted = {key: after[0].get(key) for key in expected_text} if after else {}
        checks = [('La API responde HTTP 201', response['status'] == 201),
                  ('La respuesta declara ok=true', response['body'].get('ok') is True),
                  ('SQLite contiene exactamente una nueva fila', len(after) - len(before) == 1),
                  ('Los cuatro campos se guardan sin espacios externos', persisted == expected_text),
                  ('La fila pertenece al ambiente testing', bool(after) and after[0]['environment'] == 'testing'),
                  ('El id devuelto coincide con la fila persistida', bool(after) and response['body'].get('id') == after[0]['id'])]
        self.case('I01', 'Alta válida y persistencia real en SQLite', VALID,
            {'http_status': 201, 'ok': True, 'new_rows': 1, 'stored_fields': expected_text},
            {'request': {'method': 'POST', 'path': '/api/contact'},
             'response': response, 'rows_before': before, 'rows_after': after}, checks)

    def test_I02_null_name(self):
        before = self.rows()
        response = self.post(dict(INVALID))
        after = self.rows()
        checks = [('La API responde HTTP 422', response['status'] == 422),
                  ('La respuesta declara ok=false', response['body'].get('ok') is False),
                  ('La respuesta identifica el campo name', 'name' in response['body'].get('errors', {})),
                  ('SQLite no recibe registros inválidos', len(after) == len(before) == 0)]
        self.case('I02', 'Nombre nulo por API sin inserción', INVALID,
            {'http_status': 422, 'ok': False, 'errors_contains': 'name', 'new_rows': 0},
            {'request': {'method': 'POST', 'path': '/api/contact'},
             'response': response, 'rows_before': before, 'rows_after': after}, checks)


if __name__ == '__main__':
    names = ['test_U01_valid_text', 'test_U02_null_name', 'test_I01_persistence', 'test_I02_null_name']
    suite = unittest.TestSuite(SixCaseBackend(name) for name in names)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)
