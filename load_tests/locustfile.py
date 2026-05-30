"""
Testy wydajnościowe API WeatherMood przy użyciu Locust.

Uruchomienie (z głównego katalogu projektu):
    locust -f load_tests/locustfile.py --host=http://localhost:8000

Następnie otwórz w przeglądarce:
    http://localhost:8089
i ustaw liczbę użytkowników + ramp-up (np. 50 users, 5 spawn rate).
"""
import random
from locust import HttpUser, task, between


COUNTRIES = ["Poland", "UK", "Spain", "Sweden", "Italy"]


class WeatherMoodUser(HttpUser):
    """Symulowany użytkownik dashboardu WeatherMood."""

    # Każdy "wirtualny użytkownik" czeka 1-3 sekundy między kolejnymi requestami.
    # Symuluje realne zachowanie — człowiek nie klika 100 razy na sekundę.
    wait_time = between(1, 3)

    @task(1)
    def health_check(self):
        """Endpoint /health — najlżejszy, najczęściej wołany przez monitoring."""
        self.client.get("/health")

    @task(2)
    def list_countries(self):
        """Endpoint /countries — pojedyncze proste zapytanie do bazy."""
        self.client.get("/countries")

    @task(5)
    def get_weather(self):
        """Endpoint /weather/{country} — typowy use case dashboardu."""
        country = random.choice(COUNTRIES)
        self.client.get(f"/weather/{country}", name="/weather/{country}")

    @task(5)
    def get_sentiment(self):
        """Endpoint /sentiment/{country} — typowy use case dashboardu."""
        country = random.choice(COUNTRIES)
        self.client.get(f"/sentiment/{country}", name="/sentiment/{country}")

    @task(10)
    def get_correlation(self):
        """
        Endpoint /correlation/{country} — najcięższy (dwa zapytania do bazy + agregacja).
        Wagą 10 mówimy: ten endpoint ma być testowany najmocniej, bo jest najbardziej
        obciążający dla backendu.
        """
        country = random.choice(COUNTRIES)
        self.client.get(f"/correlation/{country}", name="/correlation/{country}")