# WeatherMood

Analiza korelacji między pogodą a nastrojami społecznymi w 5 krajach Europy:
Polska, Wielka Brytania, Hiszpania, Szwecja, Włochy.

---

## Architektura

```
Open-Meteo API  ──┐
NewsAPI         ──┤──► fetcher/ ──► PostgreSQL ──► FastAPI ──► Dashboard
Currents API    ──┤
GDELT API       ──┘
```

---

## Źródła danych

| Źródło | Co dostarcza | Klucz API |
|---|---|---|
| **Open-Meteo** | Dane pogodowe — historia 30 dni (temp, opady, zachmurzenie) | Nie wymagany |
| **NewsAPI** | Nastroje medialne — nagłówki z 30 dni, sentiment przez TextBlob | Wymagany (darmowy) |
| **Currents API** | Nastroje medialne — bieżące nagłówki per kraj | Wymagany (darmowy) |
| **GDELT** | Nastroje medialne — tone score z globalnej bazy artykułów | Nie wymagany |

> GDELT bywa niestabilny — traktujemy go jako źródło uzupełniające.

---

## Konfiguracja

1. W głównym katalogu projektu utwórz plik `API_KEYS.txt`
2. Wklej klucze w poniższym formacie:

```text
newsapi: TWOJ_KLUCZ_NEWSAPI
currents: TWOJ_KLUCZ_CURRENTS
```

Rejestracja (darmowa):
- NewsAPI: https://newsapi.org/register
- Currents API: https://currentsapi.services/en/register

> **Ważne:** `API_KEYS.txt` jest w `.gitignore` — nigdy nie wypychaj kluczy do repozytorium!

---

## Instalacja

```bash
pip install requests textblob gdeltdoc
python -m textblob.download_corpora
```

---

## Uruchomienie fetcherów

### Pogoda — Open-Meteo (30 dni historii, bez klucza)
```bash
python fetcher/weather_fetcher_open_meteo.py
```

### Nastroje — NewsAPI (30 dni historii, wymaga klucza)
```bash
python fetcher/mood_fetcher_newsapi.py
```

### Nastroje — Currents API (bieżące dane, wymaga klucza)
```bash
python fetcher/mood_fetcher_current.py
```

### Nastroje — GDELT (uzupełniające, bez klucza)
```bash
python fetcher/mood_fetcher_GDELT.py
```

---

## Baza danych

Schemat bazy danych PostgreSQL znajduje się w `database/schema.sql`.

Zawiera tabele `weather` i `sentiment` oraz widok `correlation_view`
łączący obie tabele po kraju i dacie — używany przez API do endpointu `/correlation/{country}`.

```bash
psql -U postgres -d weathermood -f database/schema.sql
```

---

## Uwagi techniczne

- Open-Meteo zwraca dane dzienne per miasto; sentiment liczony jest per kraj
- NewsAPI `/v2/everything` filtruje po słowie kluczowym (nazwa kraju), nie po country code
- TextBlob liczy polarity w skali -1.0 → +1.0; GDELT używa skali -100 → +100
- Skrypty nastrojów mają wbudowane `time.sleep()` żeby nie spamować serwerów