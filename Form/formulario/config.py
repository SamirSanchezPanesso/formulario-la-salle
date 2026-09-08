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
    "development": Config("development", True, BASE_DIR / "data" / "contacts_development.db", "DEBUG"),
    "testing": Config("testing", True, BASE_DIR / "data" / "contacts_testing.db", "INFO"),
    "production": Config("production", False, BASE_DIR / "data" / "contacts_production.db", "WARNING")
}

def get_config():
    environment = os.getenv("APP_ENV", "development").strip().lower()
    return CONFIGS.get(environment, CONFIGS["development"])
