import requests
import json
import time

CITIES = ["Warsaw", "London", "Madrid", "Stockholm", "Rome"]


def fetch_media_mood(city: str, retries: int = 3) -> dict:
    url = "https://api.gdeltproject.org/api/v2/doc/doc"
    params = {
        "query": f'"{city}"',
        "mode": "ToneChart",
        "format": "json",
        "timespan": "24h"
    }

    # Udajemy standardową przeglądarkę Chrome
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    for attempt in range(retries):
        try:
            # Ustawiamy timeout: max 10 sekund na połączenie i 10 na pobranie danych
            response = requests.get(url, params=params, headers=headers, timeout=(10, 10))

            # Sprawdzamy, czy odpowiedź to faktycznie JSON (zabezpieczenie przed 'Expecting value')
            if "application/json" not in response.headers.get("Content-Type", ""):
                raise ValueError("Serwer zwrócił dane, które nie są JSON-em (pewnie strona błędu).")

            response.raise_for_status()
            return response.json()

        except requests.exceptions.Timeout:
            print(f"[{attempt + 1}/{retries}] Timeout dla {city}. Ponawiam...")
        except ValueError as e:
            print(f"[{attempt + 1}/{retries}] Zły format danych dla {city} ({e}). Ponawiam...")
        except requests.exceptions.RequestException as e:
            print(f"[{attempt + 1}/{retries}] Błąd sieciowy dla {city}. Ponawiam...")

        # Jeśli jesteśmy tutaj, znaczy że wystąpił błąd. Czekamy przed kolejną próbą.
        # Wydłużamy czas oczekiwania z każdą próbą (tzw. exponential backoff)
        time.sleep(2 ** attempt + 2)  # Czeka 3s, potem 4s, potem 6s

    return {}  # Zwracamy pusty słownik, jeśli wszystkie 3 próby zawiodą


if __name__ == "__main__":
    dataset = []

    for city in CITIES:
        data = fetch_media_mood(city)

        timeline_series = data.get("timeline", [])

        if not timeline_series or not timeline_series[0].get("data"):
            dataset.append({"city": city, "tone_score": None})
        else:
            time_points = timeline_series[0]["data"]
            latest_tone = time_points[-1]["value"]
            dataset.append({"city": city, "tone_score": latest_tone})

        # Standardowe opóźnienie, żeby nie zespamować serwera przy przechodzeniu do kolejnego miasta
        time.sleep(3)

    print(json.dumps(dataset, indent=4))