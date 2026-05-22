"""
mood_fetcher_current.py — nastroje medialne przez Currents API + TextBlob
Zastępuje poprzednią wersję z NewsAPI.org (free tier blokował kraje inne niż US).

Wymagania:
    pip install requests textblob
    python -m textblob.download_corpora   (jednorazowo)

Klucz API (darmowy, 1000 req/dzień): https://currentsapi.services/en/register
Dodaj do API_KEYS.txt w katalogu głównym projektu:
    currents: TWOJ_KLUCZ
"""

import json
import time
import logging
from pathlib import Path

import requests
from textblob import TextBlob

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger(__name__)

# Kody krajów wg Currents API (lista: https://currentsapi.services/en/docs/regions)
COUNTRIES = {
    "Poland":  "PL",
    "UK":      "GB",
    "Spain":   "ES",
    "Sweden":  "SE",
    "Italy":   "IT",
}

CURRENTS_URL = "https://api.currentsapi.services/v1/latest-news"


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


def fetch_headlines(country_code: str, api_key: str, page_size: int = 20) -> list[str]:
    """
    Pobiera nagłówki dla danego kraju z Currents API.
    Zwraca listę tytułów artykułów.
    """
    params = {
        "country":   country_code,
        "page_size": page_size,
        "language":  "en",
        "apiKey":    api_key,
    }
    response = requests.get(CURRENTS_URL, params=params, timeout=10)
    response.raise_for_status()
    data = response.json()

    if data.get("status") != "ok":
        raise ValueError(f"Currents API error: {data.get('message', 'nieznany błąd')}")

    return [
        article["title"]
        for article in data.get("news", [])
        if article.get("title")
    ]


def compute_sentiment(headlines: list[str]) -> dict:
    """
    Liczy średni sentiment z listy nagłówków przez TextBlob.
    polarity:     -1.0 (b. negatywny) → +1.0 (b. pozytywny)
    subjectivity:  0.0 (obiektywny)   →  1.0 (subiektywny)
    """
    if not headlines:
        return {"avg_polarity": None, "avg_subjectivity": None, "headline_count": 0}

    scores = [TextBlob(h).sentiment for h in headlines]
    return {
        "avg_polarity":     round(sum(s.polarity    for s in scores) / len(scores), 4),
        "avg_subjectivity": round(sum(s.subjectivity for s in scores) / len(scores), 4),
        "headline_count":   len(headlines),
    }


def fetch_country_mood(country_name: str, country_code: str, api_key: str) -> dict:
    try:
        headlines = fetch_headlines(country_code, api_key)
        sentiment = compute_sentiment(headlines)

        log.info(
            f"{country_name} ({country_code}): "
            f"polarity={sentiment['avg_polarity']}, "
            f"nagłówków={sentiment['headline_count']}"
        )
        return {
            "country":          country_name,
            "country_code":     country_code,
            "avg_polarity":     sentiment["avg_polarity"],
            "avg_subjectivity": sentiment["avg_subjectivity"],
            "headline_count":   sentiment["headline_count"],
            "source":           "currents+textblob",
        }

    except requests.exceptions.RequestException as e:
        log.error(f"{country_name}: błąd sieciowy — {e}")
        return {"country": country_name, "country_code": country_code,
                "avg_polarity": None, "source": "currents+textblob", "error": str(e)}
    except Exception as e:
        log.error(f"{country_name}: {type(e).__name__} — {e}")
        return {"country": country_name, "country_code": country_code,
                "avg_polarity": None, "source": "currents+textblob", "error": str(e)}


if __name__ == "__main__":
    api_key = get_api_key()
    dataset = []

    print(f"Pobieranie nastrojów z Currents API dla {len(COUNTRIES)} krajów...\n")

    for country_name, country_code in COUNTRIES.items():
        result = fetch_country_mood(country_name, country_code, api_key)
        dataset.append(result)
        time.sleep(1)

    print("\n--- Wyniki ---")
    print(json.dumps(dataset, indent=4))