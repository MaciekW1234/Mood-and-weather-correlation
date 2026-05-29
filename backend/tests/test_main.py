"""
Testy jednostkowe dla backendu FastAPI.

Używamy:
  - TestClient z FastAPI — pozwala wołać endpointy bez stawiania serwera.
  - app.dependency_overrides — podmieniamy get_connection na atrapę,
    żeby testy nie wymagały prawdziwej bazy danych.
"""
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.db import get_connection


# ============================================================
# Atrapa połączenia z bazą
# ============================================================

def make_fake_connection(rows):
    """
    Buduje atrapę psycopg2.connection, której kursor zwraca podane wiersze.
    Wspiera context manager (with conn.cursor() as cur:).
    """
    cursor = MagicMock()
    cursor.fetchall.return_value = rows
    # fetchone zwraca pierwszy wiersz albo None
    cursor.fetchone.return_value = rows[0] if rows else None

    # context manager: __enter__ zwraca kursor, __exit__ nic nie robi
    cursor.__enter__.return_value = cursor
    cursor.__exit__.return_value = False

    conn = MagicMock()
    conn.cursor.return_value = cursor
    return conn


def override_connection_with(rows):
    """Pomocnik: ustawia dependency override na FastAPI dla danych testowych."""
    fake = make_fake_connection(rows)
    app.dependency_overrides[get_connection] = lambda: fake
    return fake


@pytest.fixture(autouse=True)
def reset_overrides():
    """Po każdym teście czyścimy nadpisania, żeby testy się nie zaśmiecały."""
    yield
    app.dependency_overrides.clear()


client = TestClient(app)


# ============================================================
# /health — najprostszy test, bez bazy
# ============================================================

def test_health_returns_ok():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


# ============================================================
# /countries
# ============================================================

def test_countries_returns_list():
    """Baza zwraca 3 kraje → endpoint zwraca je w polu 'countries'."""
    override_connection_with([
        {"country": "Italy"},
        {"country": "Poland"},
        {"country": "UK"},
    ])

    response = client.get("/countries")

    assert response.status_code == 200
    assert response.json() == {"countries": ["Italy", "Poland", "UK"]}


def test_countries_empty_database():
    """Pusta baza → pusta lista, ale wciąż HTTP 200."""
    override_connection_with([])

    response = client.get("/countries")

    assert response.status_code == 200
    assert response.json() == {"countries": []}


# ============================================================
# /weather/{country}
# ============================================================

def test_weather_returns_records_for_country():
    """Baza zwraca dane pogodowe → endpoint zwraca listę WeatherRecord."""
    override_connection_with([
        {
            "date": "2026-05-01",
            "city": "Warsaw", "country": "Poland",
            "temp_mean": 15.5, "temp_max": 19.0, "temp_min": 10.0,
            "precipitation": 0.0, "cloudcover": 45.0,
        },
        {
            "date": "2026-05-02",
            "city": "Warsaw", "country": "Poland",
            "temp_mean": 16.5, "temp_max": 20.0, "temp_min": 11.0,
            "precipitation": 1.2, "cloudcover": 60.0,
        },
    ])

    response = client.get("/weather/Poland")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]["city"] == "Warsaw"
    assert data[0]["temp_mean"] == 15.5


def test_weather_unknown_country_returns_404():
    """Brak danych dla kraju → HTTP 404 z sensownym komunikatem."""
    override_connection_with([])

    response = client.get("/weather/Atlantis")

    assert response.status_code == 404
    assert "Atlantis" in response.json()["detail"]


# ============================================================
# /sentiment/{country}
# ============================================================

def test_sentiment_returns_records():
    override_connection_with([
        {
            "date": "2026-05-01", "country": "Poland",
            "avg_polarity": 0.12, "avg_subjectivity": 0.45,
            "headline_count": 25, "source": "currents+textblob",
        },
    ])

    response = client.get("/sentiment/Poland")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["avg_polarity"] == 0.12


def test_sentiment_unknown_country_returns_404():
    override_connection_with([])

    response = client.get("/sentiment/Atlantis")

    assert response.status_code == 404

# ============================================================
# /correlation/{country} — dwa zapytania do bazy, trzeba je zmockować osobno
# ============================================================

def test_correlation_returns_stats_and_data():
    """
    /correlation/{country} robi dwa zapytania:
      1. agregat (corr_temp, corr_cloud, days)
      2. lista punktów
    Mockujemy oba przez side_effect z listą wyników.
    """
    cursor = MagicMock()
    # fetchone zwraca wynik pierwszego execute (corr + days)
    cursor.fetchone.return_value = {
        "corr_temp": -0.032,
        "corr_cloud": 0.062,
        "days": 30,
    }
    # fetchall zwraca wynik drugiego execute (punkty)
    cursor.fetchall.return_value = [
        {"date": "2026-05-01", "temp_mean": 15.0, "cloudcover": 50.0,
         "precipitation": 0.0, "avg_polarity": 0.1},
        {"date": "2026-05-02", "temp_mean": 16.0, "cloudcover": 60.0,
         "precipitation": 1.0, "avg_polarity": 0.05},
    ]
    cursor.__enter__.return_value = cursor
    cursor.__exit__.return_value = False

    conn = MagicMock()
    conn.cursor.return_value = cursor
    app.dependency_overrides[get_connection] = lambda: conn

    response = client.get("/correlation/Poland")

    assert response.status_code == 200
    data = response.json()
    assert data["country"] == "Poland"
    assert data["days"] == 30
    assert data["corr_temp_polarity"] == -0.032
    assert data["corr_cloud_polarity"] == 0.062
    assert len(data["data"]) == 2


def test_correlation_no_data_returns_404():
    """Brak danych → 404."""
    cursor = MagicMock()
    cursor.fetchone.return_value = {"corr_temp": None, "corr_cloud": None, "days": 0}
    cursor.__enter__.return_value = cursor
    cursor.__exit__.return_value = False

    conn = MagicMock()
    conn.cursor.return_value = cursor
    app.dependency_overrides[get_connection] = lambda: conn

    response = client.get("/correlation/Atlantis")

    assert response.status_code == 404