"""
WeatherMood API — REST API wystawiające dane pogodowe, nastroje i korelacje.
Dokumentacja Swagger UI dostępna pod /docs po uruchomieniu.
"""
import logging

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.db import get_connection
from app.models import (
    WeatherRecord, SentimentRecord,
    CorrelationResponse, CorrelationPoint,
)

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger(__name__)

app = FastAPI(
    title="WeatherMood API",
    description="API do analizy korelacji między pogodą a nastrojami społecznymi.",
    version="1.0.0",
)

# CORS — pozwala frontendowi (inna domena/port) wołać to API z przeglądarki
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],      # na dev OK; w prod zawęzić do domeny frontendu
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    """Healthcheck — używany m.in. przez Docker."""
    return {"status": "ok"}


@app.get("/countries")
def get_countries():
    """Lista krajów dostępnych w bazie."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT DISTINCT country FROM weather ORDER BY country;")
            rows = cur.fetchall()
        return {"countries": [r["country"] for r in rows]}
    finally:
        conn.close()


@app.get("/weather/{country}", response_model=list[WeatherRecord])
def get_weather(country: str):
    """Dzienne dane pogodowe dla danego kraju."""
    conn = get_connection()
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


@app.get("/sentiment/{country}", response_model=list[SentimentRecord])
def get_sentiment(country: str):
    """Dzienne nastroje dla danego kraju."""
    conn = get_connection()
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


@app.get("/correlation/{country}", response_model=CorrelationResponse)
def get_correlation(country: str):
    """
    Połączone dane pogoda+nastrój dla kraju, wraz ze współczynnikami
    korelacji Pearsona (temperatura vs nastrój, zachmurzenie vs nastrój).
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            # współczynniki korelacji liczone po stronie bazy
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

            # punkty do wykresu
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