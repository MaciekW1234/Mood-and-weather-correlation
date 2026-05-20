import requests

API_KEY = "TUTAJ_WPISZ_SWOJ_KLUCZ"
CITIES = ["Warsaw", "London", "Madrid", "Stockholm", "Rome"]

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