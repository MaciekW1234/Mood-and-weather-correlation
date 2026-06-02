"""
mood_fetcher_current.py — nastroje medialne przez Currents API + TextBlob
Pobiera dane DZIENNE (jeden rekord = kraj x dzień) i zapisuje do bazy PostgreSQL.

Strategia: jedno zapytanie na kraj-dzień (Currents /search z oknem 1 dnia).
5 krajów x 30 dni = 150 zapytań/uruchomienie (limit darmowy: 1000/dobę).

Wymagania:
    pip install requests textblob psycopg2-binary
    python -m textblob.download_corpora   (jednorazowo)

Klucz API (darmowy, 1000 req/dzień): https://currentsapi.services/en/register
Dodaj do API_KEYS.txt w katalogu głównym projektu:
currents:TWOJ_KLUCZ
"""

import os
import time
import logging
from pathlib import Path
from datetime import date, timedelta, datetime, timezone
import requests
import psycopg2
from psycopg2.extras import execute_values
from textblob import TextBlob
import sys
from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

sys.path.insert(0, str(Path(__file__).parent.parent))
from logging_config import setup_logging

log = setup_logging(__name__)

# Kody krajów wg Currents API
COUNTRIES = {
    "Poland": "PL",
    "UK":     "GB",
    "Spain":  "ES",
    "Sweden": "SE",
    "Italy":  "IT",
}

CURRENTS_SEARCH_URL = "https://api.currentsapi.services/v1/search"

# Zakres dat: ostatnie 30 dni
END_DATE   = date.today() - timedelta(days=1)
START_DATE = END_DATE - timedelta(days=29) 


# Klucz API
def get_api_key() -> str:
    keys_file = Path(__file__).parent.parent / "API_KEYS.txt"
    try:
        with open(keys_file, encoding="utf-8") as f:
            for line in f:
                if line.startswith("currents:"):
                    return line.split(":", 1)[1].strip()
        raise ValueError("Klucz 'currents:' nie znaleziony w API_KEYS.txt")
    except FileNotFoundError:
        raise FileNotFoundError(f"Brak pliku: {keys_file}")


# Połączenie z bazą (Docker-friendly: czyta zmienne środowiskowe)
def get_connection():
    return psycopg2.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=os.getenv("DB_PORT", "5432"),
        dbname=os.getenv("DB_NAME", "weathermood"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
    )


# Pobieranie nagłówków dla jednego kraju i jednego dnia
def fetch_headlines_for_day(country_code: str, day: date, api_key: str, max_retries: int = 3) -> list[str]:
    #Pobiera nagłówki dla kraju z konkretnego dnia. Przy 429 (rate limit) czeka i ponawia próbę.

    start = datetime(day.year, day.month, day.day, tzinfo=timezone.utc)
    end   = start + timedelta(days=1)

    params = {
        "country":    country_code,
        "language":   "en",
        "start_date": start.isoformat().replace("+00:00", "Z"),
        "end_date":   end.isoformat().replace("+00:00", "Z"),
        "apiKey":     api_key,
    }

    for attempt in range(max_retries):
        response = requests.get(CURRENTS_SEARCH_URL, params=params, timeout=15)

        if response.status_code == 429:
            wait = (attempt + 1) * 5   # 5s, potem 10s, potem 15s
            log.warning(f"{country_code} {day}: rate limit (429), czekam {wait}s...")
            time.sleep(wait)
            continue

        response.raise_for_status()
        data = response.json()

        if str(data.get("status")) not in ("ok", "200"):
            raise ValueError(f"Currents API error: {data.get('msg', data.get('message', 'nieznany błąd'))}")

        return [a["title"] for a in data.get("news", []) if a.get("title")]

    raise requests.exceptions.RequestException(f"{country_code} {day}: przekroczono limit prób (429)")


# Liczenie sentymentu (za pomoca TextBlob)
def compute_sentiment(headlines: list[str]) -> dict:
    if not headlines:
        return {"avg_polarity": None, "avg_subjectivity": None, "headline_count": 0}

    scores = [TextBlob(h).sentiment for h in headlines]
    return {
        "avg_polarity":     round(sum(s.polarity     for s in scores) / len(scores), 4),
        "avg_subjectivity": round(sum(s.subjectivity for s in scores) / len(scores), 4),
        "headline_count":   len(headlines),
    }


# Zbieranie danych: pętla kraj x dzień
def collect_records(api_key: str) -> list[tuple]:
    #Zwraca listę krotek gotowych do zapisu w tabeli sentiment: (country, country_code, date, avg_polarity, avg_subjectivity, headline_count, source)
 
    records = []
    total_days = (END_DATE - START_DATE).days + 1

    for country_name, country_code in COUNTRIES.items():
        for i in range(total_days):
            day = START_DATE + timedelta(days=i)
            try:
                headlines = fetch_headlines_for_day(country_code, day, api_key)
                s = compute_sentiment(headlines)

                records.append((
                    country_name,
                    country_code,
                    day,
                    s["avg_polarity"],
                    s["avg_subjectivity"],
                    s["headline_count"],
                    "currents+textblob",
                ))
                log.info(f"{country_name} {day}: polarity={s['avg_polarity']}, nagłówków={s['headline_count']}")

            except requests.exceptions.RequestException as e:
                log.error(f"{country_name} {day}: błąd sieciowy — {e}")
            except Exception as e:
                log.error(f"{country_name} {day}: {type(e).__name__} — {e}")

            time.sleep(1.5)  # żeby nie przekroczyć limitu 

    return records


# Zapis do bazy (idempotentny: ON CONFLICT)
def save_to_db(records: list[tuple]) -> int:
    if not records:
        log.warning("Brak rekordów do zapisu.")
        return 0

    sql = """
        INSERT INTO sentiment
            (country, country_code, date, avg_polarity, avg_subjectivity, headline_count, source)
        VALUES %s
        ON CONFLICT (country, date, source) DO UPDATE SET
            avg_polarity     = EXCLUDED.avg_polarity,
            avg_subjectivity = EXCLUDED.avg_subjectivity,
            headline_count   = EXCLUDED.headline_count,
            country_code     = EXCLUDED.country_code;
    """

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            execute_values(cur, sql, records)
        conn.commit()
        log.info(f"Zapisano/zaktualizowano {len(records)} rekordów w tabeli sentiment.")
        return len(records)
    finally:
        conn.close()


if __name__ == "__main__":
    api_key = get_api_key()
    print(f"Pobieranie nastrojów Currents ({START_DATE} → {END_DATE}) dla {len(COUNTRIES)} krajów...\n")

    records = collect_records(api_key)
    print(f"\nZebrano {len(records)} rekordów. Zapisywanie do bazy...")

    save_to_db(records)
    print("Gotowe.")