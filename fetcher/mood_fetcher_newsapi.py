"""
mood_fetcher_newsapi.py — nastroje medialne przez NewsAPI /v2/everything + TextBlob
Używa endpointu /v2/everything (działa na free tier) zamiast /v2/top-headlines
(który blokuje kraje inne niż US na darmowym planie).

Wymagania:
    pip install requests textblob
    python -m textblob.download_corpora   (jednorazowo)

Klucz API (darmowy): https://newsapi.org/register
Dodaj do API_KEYS.txt w katalogu głównym projektu:
    newsapi: TWOJ_KLUCZ

Darmowy plan: 100 requestów/dobę, artykuły z ostatnich 30 dni.
"""

import json
import time
import logging
from datetime import date, timedelta
from pathlib import Path

import requests
from textblob import TextBlob

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger(__name__)

# Słowa kluczowe per kraj — /v2/everything nie filtruje po country code,
# więc szukamy po nazwie kraju po angielsku
COUNTRIES = {
    "Poland":  "Poland news",
    "UK":      "United Kingdom news",
    "Spain":   "Spain news",
    "Sweden":  "Sweden news",
    "Italy":   "Italy news",
}

NEWSAPI_URL = "https://newsapi.org/v2/everything"

# Zakres dat: ostatnie 30 dni (max dla free tier)
END_DATE   = date.today()
START_DATE = END_DATE - timedelta(days=29)


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


def fetch_headlines(query: str, api_key: str, page_size: int = 20) -> list[str]:
    """
    Pobiera artykuły z NewsAPI /v2/everything dla danego zapytania.
    Zwraca listę tytułów artykułów z ostatnich 30 dni.
    """
    params = {
        "q":        query,
        "language": "en",
        "pageSize": page_size,
        "sortBy":   "publishedAt",
        "from":     START_DATE.isoformat(),
        "to":       END_DATE.isoformat(),
        "apiKey":   api_key,
    }
    response = requests.get(NEWSAPI_URL, params=params, timeout=10)
    response.raise_for_status()
    data = response.json()

    if data.get("status") != "ok":
        raise ValueError(f"NewsAPI error: {data.get('message', 'nieznany błąd')}")

    return [
        article["title"]
        for article in data.get("articles", [])
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
        "avg_polarity":     round(sum(s.polarity     for s in scores) / len(scores), 4),
        "avg_subjectivity": round(sum(s.subjectivity for s in scores) / len(scores), 4),
        "headline_count":   len(headlines),
    }


def fetch_country_mood(country_name: str, query: str, api_key: str) -> dict:
    try:
        headlines = fetch_headlines(query, api_key)
        sentiment = compute_sentiment(headlines)

        log.info(
            f"{country_name}: polarity={sentiment['avg_polarity']}, "
            f"nagłówków={sentiment['headline_count']}"
        )
        return {
            "country":          country_name,
            "avg_polarity":     sentiment["avg_polarity"],
            "avg_subjectivity": sentiment["avg_subjectivity"],
            "headline_count":   sentiment["headline_count"],
            "date_range":       f"{START_DATE} → {END_DATE}",
            "source":           "newsapi+textblob",
        }

    except requests.exceptions.RequestException as e:
        log.error(f"{country_name}: błąd sieciowy — {e}")
        return {"country": country_name, "avg_polarity": None,
                "source": "newsapi+textblob", "error": str(e)}
    except Exception as e:
        log.error(f"{country_name}: {type(e).__name__} — {e}")
        return {"country": country_name, "avg_polarity": None,
                "source": "newsapi+textblob", "error": str(e)}


if __name__ == "__main__":
    api_key = get_api_key()
    dataset = []

    print(f"Pobieranie nastrojów z NewsAPI ({START_DATE} → {END_DATE})...\n")

    for country_name, query in COUNTRIES.items():
        result = fetch_country_mood(country_name, query, api_key)
        dataset.append(result)
        time.sleep(1)

    print("\n--- Wyniki ---")
    print(json.dumps(dataset, indent=4))