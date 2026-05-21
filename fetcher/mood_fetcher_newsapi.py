"""
mood_fetcher_newsapi.py — Plan B dla nastrojów medialnych
Pobiera nagłówki z NewsAPI.org i liczy sentiment lokalnie przez TextBlob.

Wymagania:
    pip install requests textblob
    python -m textblob.download_corpora  (jednorazowo, pobiera słowniki)

Klucz API (darmowy): https://newsapi.org/register
Wpisz go do pliku API_KEYS.txt w katalogu głównym projektu jako:
    newsapi: TWOJ_KLUCZ

Darmowy plan: 100 requestów/dobę, nagłówki z ostatnich 30 dni.
"""

import json
import time
import logging
from pathlib import Path

import requests
from textblob import TextBlob

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger(__name__)

# Kody krajów wg ISO 3166-1 alpha-2 (obsługiwane przez NewsAPI)
COUNTRIES = {
    "Poland": "pl",
    "UK": "gb",
    "Spain": "es",
    "Sweden": "se",
    "Italy": "it",
}


def get_api_key() -> str:
    keys_file = Path(__file__).parent.parent / "API_KEYS.txt"
    try:
        with open(keys_file, encoding="utf-8") as f:
            for line in f:
                if line.startswith("newsapi:"):
                    return line.split(":", 1)[1].strip()
        raise ValueError("Klucz 'newsapi:' nie znaleziony w API_KEYS.txt")
    except FileNotFoundError:
        raise FileNotFoundError(f"Brak pliku: {keys_file}")


def fetch_headlines(country_code: str, api_key: str, page_size: int = 20) -> list[str]:
    """
    Pobiera top nagłówki dla danego kraju z NewsAPI.
    Zwraca listę stringów (tytuły artykułów).
    """
    url = "https://newsapi.org/v2/top-headlines"
    params = {
        "country": country_code,
        "pageSize": page_size,
        "apiKey": api_key,
    }
    response = requests.get(url, params=params, timeout=10)
    response.raise_for_status()
    print("RAW:", response.json())
    data = response.json()

    if data.get("status") != "ok":
        raise ValueError(f"NewsAPI error: {data.get('message', 'nieznany błąd')}")

    headlines = [
        article["title"]
        for article in data.get("articles", [])
        if article.get("title")
    ]
    return headlines


def compute_sentiment(headlines: list[str]) -> dict:
    """
    Liczy średni sentiment z listy nagłówków przez TextBlob.
    Polarity: -1.0 (bardzo negatywny) do +1.0 (bardzo pozytywny)
    Subjectivity: 0.0 (obiektywny) do 1.0 (subiektywny)
    """
    if not headlines:
        return {"avg_polarity": None, "avg_subjectivity": None, "headline_count": 0}

    polarities = [TextBlob(h).sentiment.polarity for h in headlines]
    subjectivities = [TextBlob(h).sentiment.subjectivity for h in headlines]

    return {
        "avg_polarity": round(sum(polarities) / len(polarities), 4),
        "avg_subjectivity": round(sum(subjectivities) / len(subjectivities), 4),
        "headline_count": len(headlines),
    }


def fetch_country_mood(country_name: str, country_code: str, api_key: str) -> dict:
    """
    Główna funkcja: pobiera nagłówki i zwraca nastrój dla jednego kraju.
    """
    try:
        headlines = fetch_headlines(country_code, api_key)
        sentiment = compute_sentiment(headlines)

        log.info(
            f"{country_name} ({country_code}): "
            f"polarity={sentiment['avg_polarity']}, "
            f"nagłówków={sentiment['headline_count']}"
        )

        return {
            "country": country_name,
            "country_code": country_code,
            "avg_polarity": sentiment["avg_polarity"],
            "avg_subjectivity": sentiment["avg_subjectivity"],
            "headline_count": sentiment["headline_count"],
            "source": "newsapi+textblob",
        }

    except requests.exceptions.RequestException as e:
        log.error(f"{country_name}: błąd sieciowy — {e}")
        return {"country": country_name, "country_code": country_code, "avg_polarity": None,
                "source": "newsapi+textblob", "error": str(e)}
    except Exception as e:
        log.error(f"{country_name}: {type(e).__name__} — {e}")
        return {"country": country_name, "country_code": country_code, "avg_polarity": None,
                "source": "newsapi+textblob", "error": str(e)}


if __name__ == "__main__":
    api_key = get_api_key()
    dataset = []

    print(f"Pobieranie nastrojów z NewsAPI dla {len(COUNTRIES)} krajów...\n")

    for country_name, country_code in COUNTRIES.items():
        result = fetch_country_mood(country_name, country_code, api_key)
        dataset.append(result)
        time.sleep(1)  # grzeczne opóźnienie

    print("\n--- Wyniki ---")
    print(json.dumps(dataset, indent=4))
