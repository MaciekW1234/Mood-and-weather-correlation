"""
weather_fetcher_open_weather.py — pobieranie historycznych danych pogodowych z Open-Meteo
Zastępuje poprzednią wersję opartą na OpenWeather API.

Zalety Open-Meteo:
- Całkowicie darmowe dla zastosowań niekomercyjnych
- Bez klucza API, bez rejestracji
- Dane historyczne od 1940 roku
- Do 10 000 requestów dziennie

Wymagania:
    pip install requests

Dokumentacja: https://open-meteo.com/en/docs/historical-weather-api
"""

import json
import time
import logging
from datetime import date, timedelta

import requests

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger(__name__)

# Współrzędne miast (Open-Meteo używa lat/lon zamiast nazwy miasta)
CITIES = {
    "Warsaw":    {"country": "Poland",  "lat": 52.23,  "lon": 21.01,  "timezone": "Europe/Warsaw"},
    "London":    {"country": "UK",      "lat": 51.51,  "lon": -0.13,  "timezone": "Europe/London"},
    "Madrid":    {"country": "Spain",   "lat": 40.42,  "lon": -3.70,  "timezone": "Europe/Madrid"},
    "Stockholm": {"country": "Sweden",  "lat": 59.33,  "lon": 18.07,  "timezone": "Europe/Stockholm"},
    "Rome":      {"country": "Italy",   "lat": 41.90,  "lon": 12.50,  "timezone": "Europe/Rome"},
}

HISTORICAL_URL = "https://archive-api.open-meteo.com/v1/archive"

# Zakres dat: ostatnie 30 dni
END_DATE   = date.today() - timedelta(days=1)  # wczoraj (dziś może być niekompletny)
START_DATE = END_DATE - timedelta(days=29)      # 30 dni wstecz


def fetch_weather_history(city: str, meta: dict) -> list[dict]:
    """
    Pobiera dzienne dane pogodowe dla jednego miasta z ostatnich 30 dni.
    Zwraca listę słowników — jeden per dzień.
    """
    params = {
        "latitude":               meta["lat"],
        "longitude":              meta["lon"],
        "start_date":             START_DATE.isoformat(),
        "end_date":               END_DATE.isoformat(),
        "daily":                  "temperature_2m_mean,temperature_2m_max,temperature_2m_min,precipitation_sum,cloudcover_mean",
        "timezone":               meta["timezone"],
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
                "city":         city,
                "country":      meta["country"],
                "date":         day,
                "temp_mean":    daily["temperature_2m_mean"][i],
                "temp_max":     daily["temperature_2m_max"][i],
                "temp_min":     daily["temperature_2m_min"][i],
                "precipitation": daily["precipitation_sum"][i],
                "cloudcover":   daily["cloudcover_mean"][i],
                "source":       "open-meteo",
            })

        log.info(f"{city}: pobrano {len(records)} dni ({START_DATE} → {END_DATE})")
        return records

    except requests.exceptions.RequestException as e:
        log.error(f"{city}: błąd sieciowy — {e}")
        return []
    except Exception as e:
        log.error(f"{city}: {type(e).__name__} — {e}")
        return []


if __name__ == "__main__":
    print(f"Pobieranie danych pogodowych Open-Meteo ({START_DATE} → {END_DATE})...\n")

    all_records = []
    for city, meta in CITIES.items():
        records = fetch_weather_history(city, meta)
        all_records.extend(records)
        time.sleep(1)  # grzeczne opóźnienie

    print(f"\n--- Wyniki: {len(all_records)} rekordów łącznie ---")
    print(json.dumps(all_records[:3], indent=4))  # preview pierwszych 3
    print(f"... i {len(all_records) - 3} więcej")