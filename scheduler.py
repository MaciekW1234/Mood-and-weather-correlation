"""
scheduler.py — cykliczne pobieranie danych co 24h.
Odpala weather_fetcher_open_meteo i mood_fetcher_current jeden po drugim.

Wymagania:
    pip install schedule

Uruchomienie:
    python scheduler.py

Zatrzymanie: Ctrl+C
"""

import logging
import time
from datetime import datetime
from pathlib import Path
import sys
import schedule

sys.path.insert(0, str(Path(__file__).parent / "fetcher"))

from weather_fetcher_open_meteo import fetch_weather_history, save_to_db as save_weather, CITIES, START_DATE, END_DATE
from mood_fetcher_current import collect_records, save_to_db as save_mood, get_api_key

log = logging.getLogger(__name__)

Path("logs").mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[
        logging.FileHandler("logs/scheduler.log", encoding="utf-8"),
        logging.StreamHandler(),
    ]
)


def run_weather_fetcher():
    log.info("START: weather_fetcher_open_meteo")
    try:
        all_records = []
        for city, meta in CITIES.items():
            all_records.extend(fetch_weather_history(city, meta))
            time.sleep(1)
        inserted = save_weather(all_records)
        log.info(f"KONIEC: weather — zapisano {inserted} rekordów")
    except Exception as e:
        log.error(f"BŁĄD weather_fetcher: {e}")


def run_mood_fetcher():
    log.info("START: mood_fetcher_current")
    try:
        api_key = get_api_key()
        records = collect_records(api_key)
        inserted = save_mood(records)
        log.info(f"KONIEC: mood — zapisano {inserted} rekordów")
    except Exception as e:
        log.error(f"BŁĄD mood_fetcher: {e}")


def run_all():
    log.info(f"Cykl fetchowania: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    run_weather_fetcher()
    run_mood_fetcher()
    log.info("Cykl zakończony")


if __name__ == "__main__":
    log.info("Scheduler uruchomiony — fetchery będą odpalać się co 24h o 06:00")
    log.info("Zatrzymanie: Ctrl+C")

    # Uruchom od razu przy starcie
    run_all()

    # Potem co 24h o 06:00
    schedule.every().day.at("06:00").do(run_all)

    while True:
        schedule.run_pending()
        time.sleep(60)
