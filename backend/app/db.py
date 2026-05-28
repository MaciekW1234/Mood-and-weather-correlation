"""Połączenie z bazą PostgreSQL — wspólne dla wszystkich endpointów."""
import os
import psycopg2
from psycopg2.extras import RealDictCursor


def get_connection():
    """
    Czyta parametry ze zmiennych środowiskowych (Docker-ready),
    z fallbackiem na localhost dla pracy lokalnej.
    RealDictCursor sprawia, że wyniki to słowniki {kolumna: wartość},
    co ułatwia zwracanie JSON-a.
    """
    return psycopg2.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=os.getenv("DB_PORT", "5432"),
        dbname=os.getenv("DB_NAME", "weathermood"),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD", "postgres"),
        cursor_factory=RealDictCursor,
    )