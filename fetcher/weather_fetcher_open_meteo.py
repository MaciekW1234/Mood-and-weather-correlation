"""
weather_fetcher_open_meteo.py — historyczne dane pogodowe z Open-Meteo
Pobiera dane DZIENNE (jeden rekord = miasto x dzień) i zapisuje do bazy PostgreSQL.

Zalety Open-Meteo:
- Darmowe, bez klucza API, bez rejestracji
- Dane historyczne, do 10 000 requestów/dzień
- 30 dni jednym zapytaniem (5 zapytań na całość)

Wymagania:
    pip install requests psycopg2-binary

Dokumentacja: https://open-meteo.com/en/docs/historical-weather-api
"""

import os
import time
import logging
from datetime import date, timedelta

import requests
import psycopg2
from psycopg2.extras import execute_values

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from logging_config import setup_logging
from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent.parent / ".env")
log = setup_logging(__name__)

# Współrzędne miast (Open-Meteo używa lat/lon)
CITIES = {
    "Warsaw":    {"country": "Poland",  "lat": 52.23,  "lon": 21.01,  "timezone": "Europe/Warsaw"},
    "London":    {"country": "UK",      "lat": 51.51,  "lon": -0.13,  "timezone": "Europe/London"},
    "Madrid":    {"country": "Spain",   "lat": 40.42,  "lon": -3.70,  "timezone": "Europe/Madrid"},
    "Stockholm": {"country": "Sweden",  "lat": 59.33,  "lon": 18.07,  "timezone": "Europe/Stockholm"},
    "Rome":      {"country": "Italy",   "lat": 41.90,  "lon": 12.50,  "timezone": "Europe/Rome"},
}

HISTORICAL_URL = "https://archive-api.open-meteo.com/v1/archive"

# Zakres dat: ostatnie 30 dni
END_DATE   = date.today() - timedelta(days=1) 
START_DATE = END_DATE - timedelta(days=29)


# Połączenie z bazą (Docker-friendly: czyta zmienne środowiskowe)
def get_connection():
    return psycopg2.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=os.getenv("DB_PORT", "5432"),
        dbname=os.getenv("DB_NAME", "weathermood"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
    )


# Pobieranie danych pogodowych dla jednego miasta (30 dni jednym zapytaniem)
def fetch_weather_history(city: str, meta: dict) -> list[dict]:
    params = {
        "latitude":   meta["lat"],
        "longitude":  meta["lon"],
        "start_date": START_DATE.isoformat(),
        "end_date":   END_DATE.isoformat(),
        "daily":      "temperature_2m_mean,temperature_2m_max,temperature_2m_min,precipitation_sum,cloudcover_mean",
        "timezone":   meta["timezone"],
    }

    try:
        response = requests.get(HISTORICAL_URL, params=params, timeout=15)
        response.raise_for_status()
        data = response.json()

        daily = data.get("daily", {})
        dates = daily.get("time", [])

        if not dates:
            log.warning(f"{city}: brak danych w odpowiedzi")
            return []

        records = []
        for i, day in enumerate(dates):
            records.append({
                "city":          city,
                "country":       meta["country"],
                "date":          day,
                "temp_mean":     daily["temperature_2m_mean"][i],
                "temp_max":      daily["temperature_2m_max"][i],
                "temp_min":      daily["temperature_2m_min"][i],
                "precipitation": daily["precipitation_sum"][i],
                "cloudcover":    daily["cloudcover_mean"][i],
                "source":        "open-meteo",
            })

        log.info(f"{city}: pobrano {len(records)} dni ({START_DATE} → {END_DATE})")
        return records

    except requests.exceptions.RequestException as e:
        log.error(f"{city}: błąd sieciowy — {e}")
        return []
    except Exception as e:
        log.error(f"{city}: {type(e).__name__} — {e}")
        return []


# Zapis do bazy (idempotentny: ON CONFLICT na (city, date))
def save_to_db(records: list[dict]) -> int:
    if not records:
        log.warning("Brak rekordów do zapisu.")
        return 0

    # zamiana słowników na krotki w kolejności kolumn tabeli weather
    rows = [
        (
            r["city"], r["country"], r["date"],
            r["temp_mean"], r["temp_max"], r["temp_min"],
            r["precipitation"], r["cloudcover"], r["source"],
        )
        for r in records
    ]

    sql = """
        INSERT INTO weather
            (city, country, date, temp_mean, temp_max, temp_min,
             precipitation, cloudcover, source)
        VALUES %s
        ON CONFLICT (city, date) DO UPDATE SET
            temp_mean     = EXCLUDED.temp_mean,
            temp_max      = EXCLUDED.temp_max,
            temp_min      = EXCLUDED.temp_min,
            precipitation = EXCLUDED.precipitation,
            cloudcover    = EXCLUDED.cloudcover,
            country       = EXCLUDED.country,
            source        = EXCLUDED.source;
    """

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            execute_values(cur, sql, rows)
        conn.commit()
        log.info(f"Zapisano/zaktualizowano {len(rows)} rekordów w tabeli weather.")
        return len(rows)
    finally:
        conn.close()


if __name__ == "__main__":
    print(f"Pobieranie danych pogodowych Open-Meteo ({START_DATE} - {END_DATE})...\n")

    all_records = []
    for city, meta in CITIES.items():
        all_records.extend(fetch_weather_history(city, meta))
        time.sleep(1)  # grzeczne opóźnienie

    print(f"\nZebrano {len(all_records)} rekordów. Zapisywanie do bazy...")
    save_to_db(all_records)
    print("Gotowe.")