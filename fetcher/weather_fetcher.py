import requests
import json
from pathlib import Path

CITIES = ["Warsaw", "London", "Madrid", "Stockholm", "Rome"]


def get_api_key() -> str:
    keys_file_path = Path(__file__).parent.parent / "API_KEYS.txt"
    try:
        with open(keys_file_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.startswith("weather:"):
                    return line.split(":", 1)[1].strip()
        raise ValueError("Klucz 'weather:' nie został znaleziony w pliku API_KEYS.txt")
    except FileNotFoundError:
        raise FileNotFoundError(f"Nie znaleziono pliku z kluczami: {keys_file_path}")


API_KEY = get_api_key()


def fetch_weather(city: str) -> dict:
    url = f"https://api.openweathermap.org/data/2.5/weather"
    params = {"q": city, "appid": API_KEY, "units": "metric"}
    response = requests.get(url, params=params)
    response.raise_for_status()
    return response.json()

if __name__ == "__main__":
    for city in CITIES:
        data = fetch_weather(city)
        print(f"{city}: {data['main']['temp']}°C, {data['weather'][0]['description']}")