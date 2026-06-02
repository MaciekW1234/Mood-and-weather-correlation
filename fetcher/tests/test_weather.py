"""
Testy jednostkowe dla weather_fetcher_open_meteo.
Testowane funkcje:
  - fetch_weather_history  (z mockiem requests.get)
"""
import pytest
import requests
from unittest.mock import Mock

from weather_fetcher_open_meteo import fetch_weather_history


# Pomocnik — atrapa odpowiedzi HTTP
def _make_response(status_code=200, json_data=None):
    """Tworzy atrapę requests.Response."""
    response = Mock()
    response.status_code = status_code
    response.json.return_value = json_data or {}

    if status_code >= 400:
        response.raise_for_status.side_effect = requests.exceptions.HTTPError(
            f"{status_code} error"
        )
    else:
        response.raise_for_status.return_value = None
    return response


# Testy fetch_weather_history
WARSAW_META = {
    "country": "Poland",
    "lat": 52.23,
    "lon": 21.01,
    "timezone": "Europe/Warsaw",
}


def test_fetch_weather_happy_path(mocker):
    # Normalna odpowiedź Open-Meteo - fetcher zwraca listę rekordów per-dzień.
    fake_response = _make_response(
        status_code=200,
        json_data={
            "daily": {
                "time":                ["2026-05-01", "2026-05-02", "2026-05-03"],
                "temperature_2m_mean": [15.2, 16.8, 14.5],
                "temperature_2m_max":  [19.1, 21.3, 18.0],
                "temperature_2m_min":  [11.5, 12.4, 10.8],
                "precipitation_sum":   [0.0, 2.5, 0.8],
                "cloudcover_mean":     [45.0, 78.0, 30.0],
            }
        },
    )
    mocker.patch("weather_fetcher_open_meteo.requests.get", return_value=fake_response)

    records = fetch_weather_history("Warsaw", WARSAW_META)

    # 3 dni w odpowiedzi - 3 rekordy w wyniku
    assert len(records) == 3

    # Mapowanie pierwszego rekordu
    first = records[0]
    assert first["city"] == "Warsaw"
    assert first["country"] == "Poland"
    assert first["date"] == "2026-05-01"
    assert first["temp_mean"] == 15.2
    assert first["temp_max"] == 19.1
    assert first["temp_min"] == 11.5
    assert first["precipitation"] == 0.0
    assert first["cloudcover"] == 45.0
    assert first["source"] == "open-meteo"


def test_fetch_weather_preserves_order(mocker):
    # Rekordy mają być w kolejności dat z odpowiedzi (równoległe tablice).
    fake_response = _make_response(
        status_code=200,
        json_data={
            "daily": {
                "time":                ["2026-05-01", "2026-05-02", "2026-05-03"],
                "temperature_2m_mean": [10.0, 20.0, 30.0],
                "temperature_2m_max":  [15.0, 25.0, 35.0],
                "temperature_2m_min":  [5.0, 15.0, 25.0],
                "precipitation_sum":   [1.0, 2.0, 3.0],
                "cloudcover_mean":     [10.0, 20.0, 30.0],
            }
        },
    )
    mocker.patch("weather_fetcher_open_meteo.requests.get", return_value=fake_response)

    records = fetch_weather_history("Warsaw", WARSAW_META)

    assert records[0]["temp_mean"] == 10.0
    assert records[1]["temp_mean"] == 20.0
    assert records[2]["temp_mean"] == 30.0


def test_fetch_weather_empty_response(mocker):
    # Open-Meteo zwraca pustą listę dni - fetcher zwraca pustą listę.
    fake_response = _make_response(
        status_code=200,
        json_data={"daily": {"time": []}},
    )
    mocker.patch("weather_fetcher_open_meteo.requests.get", return_value=fake_response)

    records = fetch_weather_history("Warsaw", WARSAW_META)

    assert records == []


def test_fetch_weather_network_error_returns_empty(mocker):
    # Błąd sieciowy - fetcher loguje i zwraca pustą listę, nie crashuje.
    mocker.patch(
        "weather_fetcher_open_meteo.requests.get",
        side_effect=requests.exceptions.ConnectionError("Network down"),
    )

    records = fetch_weather_history("Warsaw", WARSAW_META)

    assert records == []


def test_fetch_weather_country_propagated_from_meta(mocker):
    # Każdy rekord ma poprawny 'country' wzięty z meta.
    fake_response = _make_response(
        status_code=200,
        json_data={
            "daily": {
                "time":                ["2026-05-01"],
                "temperature_2m_mean": [10.0],
                "temperature_2m_max":  [15.0],
                "temperature_2m_min":  [5.0],
                "precipitation_sum":   [0.0],
                "cloudcover_mean":     [50.0],
            }
        },
    )
    mocker.patch("weather_fetcher_open_meteo.requests.get", return_value=fake_response)

    italy_meta = {"country": "Italy", "lat": 41.9, "lon": 12.5, "timezone": "Europe/Rome"}
    records = fetch_weather_history("Rome", italy_meta)

    assert records[0]["city"] == "Rome"
    assert records[0]["country"] == "Italy"