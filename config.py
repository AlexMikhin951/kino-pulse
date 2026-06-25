import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent

DB_CONFIG = {
    "dbname": os.getenv("DB_NAME", "movie_analytics"),
    "user": os.getenv("DB_USER", "postgres"),
    "password": os.getenv("DB_PASSWORD", ""),
    "host": os.getenv("DB_HOST", "localhost"),
    "port": os.getenv("DB_PORT", "5432"),
}

TMDB_KEY = os.getenv("TMDB_API_KEY", "")
OMDB_KEY = os.getenv("OMDB_API_KEY", "")
KP_KEY = os.getenv("KINOPOISK_API_KEY", "")

ML32M_DIR = Path(os.getenv("ML32M_DIR", BASE_DIR / "ml-32m"))
