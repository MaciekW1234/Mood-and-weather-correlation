# WeatherMood

Analiza korelacji między pogodą a nastrojami społecznymi w 5 krajach Europy (Polska, UK, Hiszpania, Szwecja, Włochy).

## Źródła danych

- **OpenWeather API** — bieżące dane pogodowe (temperatura, ciśnienie, wilgotność, zachmurzenie)
- **Currents API** — nastroje medialne (polarity score) na podstawie analizy nagłówków prasowych per kraj
- **GDELT Doc 2.0 API** — uzupełniające nastroje medialne (Tone Score) z globalnej bazy artykułów

---

## Konfiguracja

Projekt wymaga kluczy do OpenWeatherMap oraz Currents API. GDELT nie wymaga klucza.

1. W głównym katalogu projektu utwórz plik `API_KEYS.txt`
2. Wklej klucze w poniższym formacie:

```text
weather: TWOJ_KLUCZ_OPENWEATHER
currents: TWOJ_KLUCZ_CURRENTS
```

Darmowe klucze:
- OpenWeather: https://openweathermap.org/api
- Currents API: https://currentsapi.services/en/register

> **Uwaga:** Upewnij się że `API_KEYS.txt` jest w `.gitignore` — nigdy nie wypychaj kluczy do repozytorium!

---

## Uruchomienie

Zainstaluj wymagane biblioteki:

```bash
pip install requests textblob gdeltdoc
python -m textblob.download_corpora
```

### Pobieranie danych pogodowych

```bash
python fetcher/weather_fetcher_open_weather.py
```

### Pobieranie nastrojów — Currents API (główne źródło)

```bash
python fetcher/mood_fetcher_current.py
```

### Pobieranie nastrojów — GDELT (uzupełniające)

```bash
python fetcher/mood_fetcher_GDELT.py
```

---

## Uwagi techniczne

- **Currents API** zwraca nagłówki w języku angielskim per kraj; sentiment liczony lokalnie przez TextBlob (polarity: -1.0 → +1.0)
- **GDELT** bywa niestabilny i może timeoutować — znany problem z rate limitingiem po stronie serwera
- **OpenWeather:** nowy klucz może być nieaktywny przez kilka minut do 2h po wygenerowaniu (błąd `401 Unauthorized`)
- Skrypty nastrojów mają wbudowane `time.sleep()` żeby nie spamować serwerów