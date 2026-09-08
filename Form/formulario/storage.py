import sqlite3
from datetime import datetime, timezone

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
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as connection:
        connection.execute(SCHEMA)
        connection.commit()

def save_contact(path, data, environment):
    init_database(path)
    created_at = datetime.now(timezone.utc).isoformat()
    with sqlite3.connect(path) as connection:
        cursor = connection.execute(
            "INSERT INTO contacts (name, email, subject, message, environment, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (data["name"].strip(), data["email"].strip(), data["subject"].strip(), data["message"].strip(), environment, created_at)
        )
        connection.commit()
        return cursor.lastrowid
