import os
from pathlib import Path

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")


class Config:
    FLASK_ENV = os.getenv("FLASK_ENV", "production")
    DATABASE_PATH = Path(os.getenv("DATABASE_PATH", "data/weather.db"))
    if not DATABASE_PATH.is_absolute():
        DATABASE_PATH = BASE_DIR / DATABASE_PATH
    PORT = int(os.getenv("PORT", "8000"))
    SECRET_KEY = os.getenv("SECRET_KEY", "change-me")
