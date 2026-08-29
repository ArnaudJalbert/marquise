-- Full schema for the "marquise" database.
-- Run this in the Supabase SQL Editor to set up the database from scratch.
--
-- Idempotent: every statement uses IF NOT EXISTS, so it's also safe to
-- re-run against an already-provisioned database.

CREATE SCHEMA IF NOT EXISTS marquise;

CREATE TABLE IF NOT EXISTS marquise.cinemas (
    id      TEXT PRIMARY KEY,
    name    TEXT NOT NULL,
    address TEXT,
    city    TEXT,
    website TEXT
);

CREATE TABLE IF NOT EXISTS marquise.source_definitions (
    name                TEXT PRIMARY KEY,
    display_name        TEXT NOT NULL,
    description         TEXT
);

CREATE TABLE IF NOT EXISTS marquise.cinema_source_assignments (
    cinema_id   TEXT PRIMARY KEY
        REFERENCES marquise.cinemas(id) ON DELETE CASCADE,
    source_name TEXT NOT NULL
        REFERENCES marquise.source_definitions(name) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS marquise.movies (
    id               TEXT PRIMARY KEY,
    title            TEXT NOT NULL UNIQUE,
    release_year     INTEGER,
    directors        TEXT,
    cast_members     TEXT,
    duration_minutes INTEGER,
    description      TEXT,
    poster_url       TEXT,
    trailer_url      TEXT,
    genres           TEXT,
    original_title   TEXT,
    rating           TEXT,
    origin_countries TEXT
);

CREATE TABLE IF NOT EXISTS marquise.screenings (
    id          TEXT PRIMARY KEY,
    movie_id    TEXT NOT NULL
        REFERENCES marquise.movies(id) ON DELETE CASCADE,
    cinema_id   TEXT NOT NULL
        REFERENCES marquise.cinemas(id) ON DELETE CASCADE,
    showtime    TIMESTAMP NOT NULL,
    external_id TEXT UNIQUE,
    ticket_url  TEXT,
    room        TEXT,
    language    TEXT,
    UNIQUE (cinema_id, movie_id, showtime)
);

CREATE INDEX IF NOT EXISTS idx_screenings_movie_id
    ON marquise.screenings(movie_id);

CREATE INDEX IF NOT EXISTS idx_screenings_cinema_showtime
    ON marquise.screenings(cinema_id, showtime);

CREATE INDEX IF NOT EXISTS idx_screenings_movie_showtime
    ON marquise.screenings(movie_id, showtime);

-- The primary listings and reliability audit filter by time before either
-- foreign key. Keep the identifier as a deterministic tie-breaker.
CREATE INDEX IF NOT EXISTS idx_screenings_showtime_id
    ON marquise.screenings(showtime, id);
