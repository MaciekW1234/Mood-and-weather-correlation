"""
WeatherMood API - REST API wystawiające dane pogodowe, nastroje i korelacje.
Dokumentacja Swagger UI dostępna pod /docs po uruchomieniu.
"""
import logging
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from app.db import get_connection
from app.models import (
    WeatherRecord, SentimentRecord,
    CorrelationResponse, CorrelationPoint,
)
import sys
from pathlib import Path

# logging_config leży 2 poziomy wyżej
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from logging_config import setup_logging

log = setup_logging(__name__)

app = FastAPI(
    title="WeatherMood API",
    description="""
API do analizy korelacji między warunkami pogodowymi a nastrojami społecznymi
w 5 krajach Europy: Polsce, Wielkiej Brytanii, Hiszpanii, Szwecji i Włoszech.

## Źródła danych
- **Open-Meteo** - historyczne dane pogodowe (temperatura, opady, zachmurzenie)
- **Currents API + TextBlob** - nastroje medialne na podstawie nagłówków prasowych

## Endpointy
- `/health` - healthcheck API
- `/countries` - lista dostępnych krajów
- `/weather/{country}` - dzienne dane pogodowe
- `/sentiment/{country}` - dzienne nastroje medialne
- `/correlation/{country}` - korelacja Pearsona pogoda↔nastroje + dane do wykresów
""",
    version="1.0.0",
    contact={
        "name": "WeatherMood projekt",
    },
)

# CORS pozwala frontendowi (inna domena/port) wołać to API z przeglądarki
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def log_requests(request, call_next):
    response = await call_next(request)
    log.info(f'{request.method} {request.url.path} -> {response.status_code}')
    return response

@app.get(
    "/health",
    summary="Healthcheck",
    description="Sprawdza czy API działa poprawnie. Używany przez Docker do monitorowania stanu kontenera.",
    tags=["System"],
)
def health():
    # Healthcheck
    return {"status": "ok"}


@app.get(
    "/countries",
    summary="Lista krajów",
    description="Zwraca listę wszystkich krajów dla których dostępne są dane w bazie.",
    tags=["Dane"],
)
def get_countries(conn = Depends(get_connection)):
    # Lista krajów dostępnych w bazie.
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT DISTINCT country FROM weather ORDER BY country;")
            rows = cur.fetchall()
        return {"countries": [r["country"] for r in rows]}
    finally:
        conn.close()


@app.get(
    "/weather/{country}",
    response_model=list[WeatherRecord],
    summary="Dane pogodowe dla kraju",
    description="""
Zwraca dzienne dane pogodowe dla wybranego kraju z ostatnich 30 dni.
Źródło: **Open-Meteo Historical API** (bez klucza API).
Dostępne kraje: `Poland`, `UK`, `Spain`, `Sweden`, `Italy`
""",
    response_description="Lista dziennych rekordów pogodowych posortowana po dacie.",
    tags=["Dane"],
)
def get_weather(country: str, conn = Depends(get_connection)):
    # Dzienne dane pogodowe dla danego kraju.
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT date, city, country, temp_mean, temp_max, temp_min,
                       precipitation, cloudcover
                FROM weather
                WHERE country = %s
                ORDER BY date;
                """,
                (country,),
            )
            rows = cur.fetchall()
        if not rows:
            raise HTTPException(status_code=404, detail=f"Brak danych pogodowych dla: {country}")
        return rows
    finally:
        conn.close()


@app.get(
    "/sentiment/{country}",
    response_model=list[SentimentRecord],
    summary="Nastroje medialne dla kraju",
    description="""
    Zwraca dzienne nastroje medialne dla wybranego kraju z ostatnich 30 dni.
    Sentiment liczony lokalnie przez **TextBlob** na podstawie nagłówków prasowych
    pobranych z **Currents API**.
    - `avg_polarity`: -1.0 (bardzo negatywny) -- +1.0 (bardzo pozytywny)
    - `avg_subjectivity`: 0.0 (obiektywny) -- 1.0 (subiektywny)
    Dostępne kraje: `Poland`, `UK`, `Spain`, `Sweden`, `Italy`
    """,
    response_description="Lista dziennych rekordów nastrojów posortowana po dacie.",
    tags=["Dane"],
)
def get_sentiment(country: str, conn = Depends(get_connection)):
    # dzienne nastroje dla danego kraju
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT date, country, avg_polarity, avg_subjectivity,
                       headline_count, source
                FROM sentiment
                WHERE country = %s
                ORDER BY date;
                """,
                (country,),
            )
            rows = cur.fetchall()
        if not rows:
            raise HTTPException(status_code=404, detail=f"Brak danych nastrojów dla: {country}")
        return rows
    finally:
        conn.close()


@app.get(
    "/correlation/{country}",
    response_model=CorrelationResponse,
    summary="Korelacja pogoda↔nastroje",
    description="""
    Zwraca współczynniki korelacji Pearsona między warunkami pogodowymi
    a nastrojami medialnymi dla wybranego kraju oraz punkty danych do wykresu.

    ## Współczynniki korelacji
    - `corr_temp_polarity`: korelacja temperatury z nastrojem
    - `corr_cloud_polarity`: korelacja zachmurzenia z nastrojem

    Wartości: -1.0 (silna ujemna) -- 0 (brak) -- +1.0 (silna dodatnia)

    Korelacja liczona funkcją PostgreSQL `corr()` na widoku `correlation_view`.

    Dostępne kraje: `Poland`, `UK`, `Spain`, `Sweden`, `Italy`
    """,
    response_description="Współczynniki korelacji oraz lista punktów danych do wykresu.",
    tags=["Analiza"],
)
def get_correlation(country: str, conn = Depends(get_connection)):
    # połączone dane pogoda+nastrój dla kraju, wraz ze współczynnikami korelacji Pearsona (temperatura vs nastrój, zachmurzenie vs nastrój)

    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    corr(temp_mean, avg_polarity)  AS corr_temp,
                    corr(cloudcover, avg_polarity) AS corr_cloud,
                    COUNT(*)                        AS days
                FROM correlation_view
                WHERE country = %s;
                """,
                (country,),
            )
            stats = cur.fetchone()

            if not stats or stats["days"] == 0:
                raise HTTPException(status_code=404, detail=f"Brak danych korelacji dla: {country}")

            cur.execute(
                """
                SELECT date, temp_mean, cloudcover, precipitation, avg_polarity
                FROM correlation_view
                WHERE country = %s
                ORDER BY date;
                """,
                (country,),
            )
            points = cur.fetchall()

        return CorrelationResponse(
            country=country,
            days=stats["days"],
            corr_temp_polarity=round(stats["corr_temp"], 4) if stats["corr_temp"] is not None else None,
            corr_cloud_polarity=round(stats["corr_cloud"], 4) if stats["corr_cloud"] is not None else None,
            data=[CorrelationPoint(**p) for p in points],
        )
    finally:
        conn.close()