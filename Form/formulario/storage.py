"""Almacenamiento SQLite compatible con la tabla de la versión original."""

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS contacts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT NOT NULL,
    subject TEXT NOT NULL,
    message TEXT NOT NULL,
    environment TEXT NOT NULL,
    created_at TEXT NOT NULL
)
"""


def init_database(path):
    """Crea la tabla solamente si falta; nunca borra mensajes existentes."""
    ruta = Path(path)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(ruta, timeout=5) as conexion:
        conexion.execute(SCHEMA)


def save_contact(path, data, environment):
    """Guarda un contacto validado y devuelve su identificador.

    Los parámetros SQL impiden interpretar texto como instrucciones SQL.
    Se abre una conexión por operación para no compartirla entre hilos.
    La fecha se conserva en UTC y la estructura de la base sigue siendo igual.
    """
    init_database(path)
    fecha = datetime.now(timezone.utc).isoformat()
    with sqlite3.connect(path, timeout=5) as conexion:
        cursor = conexion.execute(
            "INSERT INTO contacts "
            "(name, email, subject, message, environment, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (
                data["name"].strip(), data["email"].strip(),
                data["subject"].strip(), data["message"].strip(),
                environment, fecha,
            ),
        )
        return cursor.lastrowid
