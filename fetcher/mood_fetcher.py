"""
mood_fetcher.py — pobieranie nastrojów medialnych z GDELT Doc API
Używa biblioteki gdeltdoc (pip install gdeltdoc) zamiast surowych requestów.

ZNANY PROBLEM: GDELT blokuje requesty z serwerów datacenter (403).
Działa lokalnie na komputerze użytkownika, może nie działać w Dockerze/VPS.
Plan B: mood_fetcher_newsapi.py (NewsAPI + TextBlob)
"""

import json
import time
from datetime import date, timedelta

try:
    from gdeltdoc import GdeltDoc, Filters
except ImportError:
    raise ImportError("Zainstaluj bibliotekę: pip install gdeltdoc")

COUNTRIES = {
    "Poland": "Warsaw",
    "UK": "London",
    "Spain": "Madrid",
    "Sweden": "Stockholm",
    "Italy": "Rome Italy",
}

# Zakres dat: ostatnie 7 dni (GDELT wymaga min. kilku dni dla stabilnych wyników)
END_DATE = date.today()
START_DATE = END_DATE - timedelta(days=7)


def fetch_tone(country_name: str, city: str) -> dict:
    """
    Pobiera średni tone score z GDELT dla danego miasta z ostatnich 7 dni.
    Zwraca słownik z country, city, avg_tone, data_points lub błędem.
    """
    gd = GdeltDoc()
    f = Filters(
        keyword=city,
        start_date=START_DATE.strftime("%Y-%m-%d"),
        end_date=END_DATE.strftime("%Y-%m-%d"),
    )

    try:
        timeline = gd.timeline_search("timelinetone", f)

        if timeline is None or timeline.empty:
            print(f"[WARN] Brak danych dla {city}")
            return {"country": country_name, "city": city, "avg_tone": None, "data_points": 0, "source": "gdelt"}

        # Kolumna z tonem nazywa się "Average Tone" w bibliotece gdeltdoc
        tone_col = "Average Tone" if "Average Tone" in timeline.columns else timeline.columns[1]
        avg_tone = round(float(timeline[tone_col].mean()), 4)
        data_points = len(timeline)

        print(f"[OK] {city}: avg_tone={avg_tone}, punktów danych={data_points}")
        return {
            "country": country_name,
            "city": city,
            "avg_tone": avg_tone,
            "data_points": data_points,
            "source": "gdelt",
        }

    except Exception as e:
        print(f"[ERROR] {city}: {type(e).__name__} — {e}")
        return {"country": country_name, "city": city, "avg_tone": None, "data_points": 0, "source": "gdelt",
                "error": str(e)}


if __name__ == "__main__":
    print(f"Pobieranie danych GDELT ({START_DATE} → {END_DATE})...\n")
    dataset = []

    for country, city in COUNTRIES.items():
        result = fetch_tone(country, city)
        dataset.append(result)
        time.sleep(5)  # grzeczne opóźnienie między requestami

    print("\n--- Wyniki ---")
    print(json.dumps(dataset, indent=4))
