-- =============================================================
-- WeatherMood — schemat bazy danych PostgreSQL
-- =============================================================
-- Uruchomienie:
--   psql -U postgres -d weathermood -f schema.sql
-- Lub przez pgAdmin: Tools → Query Tool → wklej i wykonaj
-- =============================================================

-- Tworzymy bazę jeśli nie istnieje (wykonaj osobno jako superuser)
-- CREATE DATABASE weathermood;

-- -------------------------------------------------------------
-- Tabela: weather
-- Źródło: Open-Meteo Historical API (bez klucza)
-- Granularność: 1 rekord = 1 miasto x 1 dzień
-- -------------------------------------------------------------
CREATE TABLE IF NOT EXISTS weather (
    id              SERIAL PRIMARY KEY,
    city            VARCHAR(100)   NOT NULL,
    country         VARCHAR(100)   NOT NULL,
    date            DATE           NOT NULL,
    temp_mean       REAL,                        -- średnia temperatura [°C]
    temp_max        REAL,                        -- max temperatura [°C]
    temp_min        REAL,                        -- min temperatura [°C]
    precipitation   REAL,                        -- suma opadów [mm]
    cloudcover      REAL,                        -- zachmurzenie [%]
    source          VARCHAR(50)    DEFAULT 'open-meteo',
    created_at      TIMESTAMP      DEFAULT NOW(),

    UNIQUE (city, date)                          -- zapobiega duplikatom przy ponownym fetchowaniu
);

-- -------------------------------------------------------------
-- Tabela: sentiment
-- Źródło: NewsAPI /v2/everything + TextBlob (główne)
--         Currents API + TextBlob (uzupełniające)
--         GDELT Doc API (uzupełniające, gdy dostępne)
-- Granularność: 1 rekord = 1 kraj x 1 dzień x 1 źródło
-- -------------------------------------------------------------
CREATE TABLE IF NOT EXISTS sentiment (
    id              SERIAL PRIMARY KEY,
    country         VARCHAR(100)   NOT NULL,
    country_code    VARCHAR(10),                 -- ISO kod kraju np. PL, GB
    date            DATE           NOT NULL,
    avg_polarity    REAL,                        -- TextBlob: -1.0 (neg) → +1.0 (poz)
    avg_subjectivity REAL,                       -- TextBlob: 0.0 (obj) → 1.0 (subj)
    avg_tone        REAL,                        -- GDELT tone: -100 → +100
    headline_count  INTEGER,                     -- liczba artykułów/nagłówków
    source          VARCHAR(50)    NOT NULL,     -- newsapi+textblob / currents+textblob / gdelt
    created_at      TIMESTAMP      DEFAULT NOW(),

    UNIQUE (country, date, source)               -- jeden rekord per kraj x dzień x źródło
);

-- -------------------------------------------------------------
-- Widok: correlation_view
-- Łączy pogodę z nastrojami po kraju i dacie
-- Używany przez FastAPI do endpointu /correlation/{country}
-- -------------------------------------------------------------
CREATE OR REPLACE VIEW correlation_view AS
SELECT
    w.date,
    w.city,
    w.country,
    w.temp_mean,
    w.temp_max,
    w.temp_min,
    w.precipitation,
    w.cloudcover,
    s.avg_polarity,
    s.avg_subjectivity,
    s.avg_tone,
    s.headline_count,
    s.source        AS sentiment_source
FROM weather w
JOIN sentiment s
    ON w.country = s.country
    AND w.date   = s.date
ORDER BY w.country, w.date;

-- -------------------------------------------------------------
-- Indeksy dla szybszych zapytań
-- -------------------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_weather_country_date
    ON weather (country, date);

CREATE INDEX IF NOT EXISTS idx_sentiment_country_date
    ON sentiment (country, date);

-- -------------------------------------------------------------
-- Przykładowe zapytania kontrolne (zakomentowane)
-- -------------------------------------------------------------
-- SELECT country, COUNT(*) as dni FROM weather GROUP BY country;
-- SELECT country, source, COUNT(*) as dni FROM sentiment GROUP BY country, source;
-- SELECT * FROM correlation_view WHERE country = 'Poland' LIMIT 10;