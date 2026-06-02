# WeatherMood — Weather & Mood Correlation

Analiza korelacji między warunkami pogodowymi a nastrojami społecznymi
w 5 krajach Europy: Polsce, Wielkiej Brytanii, Hiszpanii, Szwecji i Włoszech.

Projekt realizowany w ramach przedmiotu Inżynieria i Analiza Danych
na Wydziale Matematyki i Nauk Informacyjnych Politechniki Warszawskiej.

---

## Jak to działa

System pobiera dzienne dane pogodowe z Open-Meteo (temperatura, opady,
zachmurzenie) oraz nastroje medialne z Currents API (sentiment nagłówków
prasowych liczony przez TextBlob). Dane trafiają do PostgreSQL, skąd
FastAPI udostępnia je przez REST API, a dashboard w przeglądarce
pokazuje wykresy korelacji dla każdego kraju.

---

## Technologie

| Warstwa | Technologia |
|---|---|
| Dane pogodowe | Open-Meteo Historical API (bez klucza) |
| Dane nastrojów | Currents API + TextBlob |
| Baza danych | PostgreSQL 16 |
| Backend | FastAPI (Python 3.12) |
| Frontend | HTML + JS + Chart.js |
| Konteneryzacja | Docker + docker-compose |
| Testy | pytest + locust |
| Scheduler | schedule (Python) |

---

## Struktura projektu

```
Mood-and-weather-correlation/
├── backend/
│   ├── app/
│   │   ├── main.py          # FastAPI — endpointy REST
│   │   ├── db.py            # połączenie z PostgreSQL
│   │   └── models.py        # modele Pydantic / Swagger
│   ├── tests/
│   │   └── test_main.py     # testy jednostkowe
│   ├── Dockerfile
│   └── requirements.txt
├── database/
│   └── schema.sql           # tabele weather, sentiment, widok correlation_view
├── docker/
│   ├── .env.example
│   ├── docker-compose.base.yml
│   ├── docker-compose.dev.yml
│   ├── docker-compose.test.yml
│   └── docker-compose.prod.yml
├── fetcher/
│   ├── tests/               # testy jednostkowe fetcherów
│   ├── weather_fetcher_open_meteo.py
│   └── mood_fetcher_current.py
├── frontend/
│   └── src/
│       ├── index.html
│       ├── app.js
│       └── style.css
├── load_tests/
│   └── locustfile.py        # testy wydajnościowe API
├── logs/
│   └── scheduler.log
├── scheduler.py             # cykliczne fetchowanie co 24h
├── logging_config.py
├── Makefile
└── requirements.txt
```

---

## Uruchomienie

### Wymagania

- Docker Desktop
- Python 3.12+
- Klucz Currents API (darmowy): https://currentsapi.services/en/register

### Konfiguracja

Stwórz plik `docker/.env` na podstawie `docker/.env.example`:

```
POSTGRES_DB=weathermood
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
```

Stwórz plik `API_KEYS.txt` w głównym katalogu projektu:

```
currents: TWOJ_KLUCZ_CURRENTS
```

> `API_KEYS.txt` jest w `.gitignore` — nie wypychaj kluczy do repozytorium.

### Konfiguracja zmiennych środowiskowych (.env)

Zanim uruchomisz projekt, musisz skonfigurować połączenie z bazą danych. W głównym katalogu projektu (tam, gdzie znajduje się ten plik README) utwórz nowy plik o nazwie `.env`. 

Dla domyślnego, lokalnego uruchomienia bazy PostgreSQL wpisz w nim następujące dane (użytkownik i hasło to `postgres`):

```env
DB_HOST=localhost
DB_PORT=5432
DB_NAME=weathermood
DB_USER=postgres
DB_PASSWORD=postgres
```
### Instalacja zależności

```bash
pip install -r requirements.txt
python -m textblob.download_corpora
```

### Uruchomienie środowiska dev

```bash
git clone https://github.com/MaciekW1234/Mood-and-weather-correlation
cd Mood-and-weather-correlation

docker compose -f docker/docker-compose.base.yml -f docker/docker-compose.dev.yml up -d
```

### Zasilenie bazy danych (jednorazowe)

```bash
python fetcher/weather_fetcher_open_meteo.py
python fetcher/mood_fetcher_current.py
```

### Dostęp do aplikacji

| Serwis | Adres |
|---|---|
| Dashboard | http://localhost:3000 |
| REST API | http://localhost:8000 |
| Swagger UI | http://localhost:8000/docs |

---

## REST API

| Endpoint | Opis |
|---|---|
| `GET /health` | Healthcheck |
| `GET /countries` | Lista dostępnych krajów |
| `GET /weather/{country}` | Dzienne dane pogodowe (30 dni) |
| `GET /sentiment/{country}` | Dzienne nastroje medialne (30 dni) |
| `GET /correlation/{country}` | Korelacja Pearsona + dane do wykresów |

Pełna dokumentacja interaktywna dostępna pod `/docs` (Swagger UI).

---

## Środowiska

Projekt obsługuje trzy środowiska Docker:

```bash
# dev — lokalne środowisko deweloperskie
docker compose -f docker/docker-compose.base.yml -f docker/docker-compose.dev.yml up -d

# test — izolowana baza w tmpfs (dane nie są zapisywane)
docker compose -f docker/docker-compose.base.yml -f docker/docker-compose.test.yml up -d

# prod — z healthcheckiem i restart: unless-stopped
docker compose -f docker/docker-compose.base.yml -f docker/docker-compose.prod.yml up -d
```

---

## Testy

### Testy jednostkowe

```bash
pytest
```

### Testy wydajnościowe (locust)

```bash
locust -f load_tests/locustfile.py --host=http://localhost:8000
```

Następnie otwórz http://localhost:8089 i skonfiguruj liczbę użytkowników.

---

## Scheduler

Automatyczne fetchowanie danych co 24h (domyślnie o 06:00):

```bash
python scheduler.py
```

Logi zapisywane do `logs/scheduler.log`.

---

## Autorzy

- **Maciej** — infrastruktura (Docker, środowiska), backend REST API
  (FastAPI, endpointy, Swagger), baza danych (schema, widoki), frontendgit, testy jednostkowe, testy wydajnościowe, logowanie
- **Kacper** — fetchery danych (Open-Meteo, Currents API), scheduler, integracja z bazą danych, dokumentacja, frontend (dashboard, wykresy)

---

## Licencja

MIT
