# WeatherMood

Analiza korelacji między pogodą a nastrojami społecznymi w 5 miastach Europy (Warszawa, Londyn, Madryt, Sztokholm, Rzym).

## Źródła danych
- **OpenWeather API** — bieżące dane pogodowe (temperatura, ciśnienie, wilgotność).
- **GDELT Doc 2.0 API** — nastroje medialne (Tone Score) na podstawie analizy artykułów z ostatnich 24 godzin.

---

## Konfiguracja (Ważne przed uruchomieniem!)

Projekt wymaga klucza autoryzacyjnego do OpenWeatherMap. GDELT API jest w 100% darmowe i nie wymaga logowania.

1. W głównym katalogu projektu (jeden poziom wyżej niż folder `fetcher`) utwórz plik tekstowy o nazwie `API_KEYS.txt`.
2. Wklej do niego swój klucz w poniższym formacie (zwróć uwagę na brak nawiasów i pustych znaków):

   ```text
   weather: TWOJ_KLUCZ_API_OPENWEATHER_TUTAJ
   
```

> **Uwaga dla kontrybutorów:** Upewnijcie się, że plik `API_KEYS.txt` znajduje się w waszym lokalnym pliku `.gitignore`, aby przypadkowo nie wypchnąć kluczy do repozytorium!

---

## Uruchomienie

Najpierw zainstaluj wymagane biblioteki:

```bash
pip install requests
```

### Pobieranie danych pogodowych
Zwraca surowe dane ustrukturyzowane w formacie JSON, gotowe do zasilenia bazy danych.

```bash
python fetcher/weather_fetcher.py
```

### Pobieranie danych o nastrojach
Zwraca wskaźnik Tone Score dla zdefiniowanych miast w formacie JSON.

```bash
python fetcher/mood_fetcher.py
```

---

## Uwagi techniczne
* **Rate Limits (GDELT):** Skrypt `mood_fetcher.py` celowo usypia się na 3 sekundy po każdym mieście (`time.sleep(3)`). Zabezpiecza to przed nałożeniem blokady i błędem `429 Too Many Requests`.
* **Konta OpenWeather:** Jeśli wygenerowałeś nowy klucz OpenWeatherMap, jego pełna aktywacja po stronie serwerów może zająć od kilku minut do 2 godzin. Do tego czasu API może zwracać błąd `401 Unauthorized`.