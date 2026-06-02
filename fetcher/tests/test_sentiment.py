"""
Testy jednostkowe dla mood_fetcher_current.
Testowane funkcje:
  - compute_sentiment   (czysta funkcja, bez mocków)
  - fetch_headlines_for_day  (z mockiem requests.get)
"""
import pytest
from mood_fetcher_current import compute_sentiment
from datetime import date
from mood_fetcher_current import fetch_headlines_for_day
import requests
from unittest.mock import Mock


# Testy compute_sentiment — czysta funkcja, bez mocków
def test_compute_sentiment_empty_list():
    # Pusta lista nagłówków - polarity i subjectivity = None, count = 0.
    result = compute_sentiment([])

    assert result["avg_polarity"] is None
    assert result["avg_subjectivity"] is None
    assert result["headline_count"] == 0


def test_compute_sentiment_single_headline():
    # Jeden nagłówek - polarity to liczba w [-1, 1].
    result = compute_sentiment(["Today is a wonderful and amazing day!"])

    assert result["headline_count"] == 1
    assert isinstance(result["avg_polarity"], float)
    assert -1.0 <= result["avg_polarity"] <= 1.0
    assert 0.0 <= result["avg_subjectivity"] <= 1.0


def test_compute_sentiment_positive_text_has_positive_polarity():
    # Zdecydowanie pozytywne nagłówki - dodatnia polaryzacja.
    headlines = [
        "Wonderful news, great success and amazing achievement!",
        "Excellent results, brilliant performance, fantastic outcome!",
    ]
    result = compute_sentiment(headlines)

    assert result["avg_polarity"] > 0


def test_compute_sentiment_negative_text_has_negative_polarity():
    # Zdecydowanie negatywne nagłówki - ujemna polaryzacja.
    headlines = [
        "Terrible disaster, awful tragedy, horrible outcome.",
        "Worst news ever, devastating loss, painful defeat.",
    ]
    result = compute_sentiment(headlines)

    assert result["avg_polarity"] < 0


def test_compute_sentiment_headline_count_matches():
    # headline_count powinien odpowiadać liczbie wejściowych nagłówków.
    headlines = ["a", "b", "c", "d", "e"]
    result = compute_sentiment(headlines)

    assert result["headline_count"] == 5


# Testy fetch_headlines_for_day — z mockowaniem requests.get
def _make_response(status_code=200, json_data=None):
    """
    Pomocnik: tworzy "atrapę" obiektu Response, który ma:
      - status_code (int),
      - .json() zwracającą json_data,
      - .raise_for_status() która rzuca błąd dla 4xx/5xx.
    Używamy unittest.mock.Mock przez fixture `mocker`.
    """

    response = Mock()
    response.status_code = status_code
    response.json.return_value = json_data or {}

    # raise_for_status — udaje zachowanie requests:
    # dla 200 nie robi nic, dla 4xx/5xx rzuca HTTPError
    if status_code >= 400:
        response.raise_for_status.side_effect = requests.exceptions.HTTPError(
            f"{status_code} error"
        )
    else:
        response.raise_for_status.return_value = None

    return response


def test_fetch_headlines_happy_path(mocker):
    # API zwraca normalną odpowiedź - fetcher wyciąga tytuły.
    fake_response = _make_response(
        status_code=200,
        json_data={
            "status": "ok",
            "news": [
                {"title": "First headline"},
                {"title": "Second headline"},
                {"title": "Third headline"},
            ],
        },
    )
    mocker.patch("mood_fetcher_current.requests.get", return_value=fake_response)

    result = fetch_headlines_for_day("PL", date(2026, 5, 15), "fake_key")

    assert result == ["First headline", "Second headline", "Third headline"]


def test_fetch_headlines_filters_empty_titles(mocker):
    """Artykuły bez pola 'title' albo z pustym tytułem są pomijane."""
    fake_response = _make_response(
        status_code=200,
        json_data={
            "status": "ok",
            "news": [
                {"title": "Valid headline"},
                {"title": ""},          # pusty tytuł
                {"author": "Anon"},     # brak pola title
                {"title": "Another valid"},
            ],
        },
    )
    mocker.patch("mood_fetcher_current.requests.get", return_value=fake_response)

    result = fetch_headlines_for_day("PL", date(2026, 5, 15), "fake_key")

    assert result == ["Valid headline", "Another valid"]


def test_fetch_headlines_retries_on_429(mocker):
    """Pierwsza próba: 429. Druga: 200 z danymi. Fetcher powinien ponowić i zwrócić dane."""
    # Pierwsza odpowiedź: rate limit
    response_429 = _make_response(status_code=429)
    # Druga odpowiedź: sukces
    response_ok = _make_response(
        status_code=200,
        json_data={"status": "ok", "news": [{"title": "Got it on retry"}]},
    )

    # side_effect z listą → kolejne wywołania zwracają kolejne elementy
    mocker.patch(
        "mood_fetcher_current.requests.get",
        side_effect=[response_429, response_ok],
    )
    # Zmockujmy też time.sleep, żeby test nie czekał 5 sekund:
    mocker.patch("mood_fetcher_current.time.sleep")

    result = fetch_headlines_for_day("PL", date(2026, 5, 15), "fake_key")

    assert result == ["Got it on retry"]


def test_fetch_headlines_raises_on_api_error_status(mocker):
    """API zwraca status != 'ok' → fetcher rzuca ValueError."""
    fake_response = _make_response(
        status_code=200,
        json_data={"status": "error", "msg": "Invalid parameters"},
    )
    mocker.patch("mood_fetcher_current.requests.get", return_value=fake_response)

    with pytest.raises(ValueError, match="Invalid parameters"):
        fetch_headlines_for_day("PL", date(2026, 5, 15), "fake_key")


