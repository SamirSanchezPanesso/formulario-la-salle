"""Configuración de los tres ambientes sin dependencias externas.

Las variables se leen del entorno del proceso. El archivo .env.example es una
guía de valores: Python no lo carga automáticamente.
"""

import os
from dataclasses import dataclass
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent


@dataclass(frozen=True)
class Config:
    name: str
    debug: bool
    database: Path
    log_level: str


CONFIGS = {
    "development": Config(
        "development", True, BASE_DIR / "data" / "contacts_development.db", "DEBUG"
    ),
    "testing": Config(
        "testing", True, BASE_DIR / "data" / "contacts_testing.db", "INFO"
    ),
    "production": Config(
        "production", False, BASE_DIR / "data" / "contacts_production.db", "WARNING"
    ),
}


def get_config():
    """Rechaza errores de escritura para no arrancar otro ambiente por accidente."""
    ambiente = os.getenv("APP_ENV", "development").strip().lower()
    if ambiente not in CONFIGS:
        raise ValueError(
            "APP_ENV debe ser development, testing o production; "
            f"se recibió {ambiente!r}."
        )

    base = CONFIGS[ambiente]
    ruta_indicada = os.getenv("DATABASE_PATH", "").strip()
    if not ruta_indicada:
        return base

    # Una ruta relativa siempre se interpreta respecto de esta aplicación,
    # sin depender del directorio desde el cual se ejecute el comando.
    ruta = Path(ruta_indicada).expanduser()
    if not ruta.is_absolute():
        ruta = BASE_DIR / ruta
    return Config(base.name, base.debug, ruta.resolve(), base.log_level)
