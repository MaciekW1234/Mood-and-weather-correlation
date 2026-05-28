"""Modele Pydantic — definiują kształt odpowiedzi JSON i zasilają Swagger UI."""
from datetime import date
from pydantic import BaseModel


class WeatherRecord(BaseModel):
    date: date
    city: str
    country: str
    temp_mean: float | None
    temp_max: float | None
    temp_min: float | None
    precipitation: float | None
    cloudcover: float | None


class SentimentRecord(BaseModel):
    date: date
    country: str
    avg_polarity: float | None
    avg_subjectivity: float | None
    headline_count: int | None
    source: str


class CorrelationPoint(BaseModel):
    date: date
    temp_mean: float | None
    cloudcover: float | None
    precipitation: float | None
    avg_polarity: float | None


class CorrelationResponse(BaseModel):
    country: str
    days: int
    corr_temp_polarity: float | None
    corr_cloud_polarity: float | None
    data: list[CorrelationPoint]