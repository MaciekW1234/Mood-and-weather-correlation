"""
Wspólna konfiguracja logowania dla całego projektu WeatherMood.
Każdy moduł importuje setup_logging() i woła ją raz na początku.

Format:
    YYYY-MM-DD HH:MM:SS | LEVEL    | module_name           | message

Poziom logowania kontrolowany przez zmienną LOG_LEVEL (domyślnie INFO).
"""
import logging
import os
import sys


LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)-25s | %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def setup_logging(name: str | None = None) -> logging.Logger:
    """
    Konfiguruje root logger w jednolitym formacie i zwraca logger dla danego modułu.

    Args:
        name: nazwa loggera (zwykle __name__). Jeśli None, zwracany jest root logger.

    Returns:
        logging.Logger gotowy do użycia.
    """
    level_name = os.getenv("LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)

    # Konfigurujemy tylko raz - przy kolejnych wywołaniach handlery są już ustawione.
    root = logging.getLogger()
    if not root.handlers:
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT)
        handler.setFormatter(formatter)
        root.addHandler(handler)
        root.setLevel(level)

    return logging.getLogger(name)