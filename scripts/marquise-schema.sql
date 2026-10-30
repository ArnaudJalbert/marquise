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
    origin_countries TEXT,
    tmdb_id          TEXT UNIQUE
);

CREATE TABLE IF NOT EXISTS marquise.screenings (
    id          TEXT PRIMARY KEY,
    movie_id    TEXT NOT NULL
        REFERENCES marquise.movies(id) ON DELETE CASCADE,
    cinema_id   TEXT NOT NULL
        REFERENCES marquise.cinemas(id) ON DELETE CASCADE,
    showtime    TIMESTAMP NOT NULL,
    external_id TEXT,
    source_name TEXT
        REFERENCES marquise.source_definitions(name) ON DELETE SET NULL,
    ticket_url  TEXT,
    room        TEXT,
    language    TEXT,
    UNIQUE (cinema_id, movie_id, showtime),
    CONSTRAINT screenings_external_id_key UNIQUE (cinema_id, external_id)
);

CREATE INDEX IF NOT EXISTS idx_screenings_movie_id
    ON marquise.screenings(movie_id);

CREATE INDEX IF NOT EXISTS idx_screenings_cinema_showtime
    ON marquise.screenings(cinema_id, showtime);

CREATE INDEX IF NOT EXISTS idx_screenings_movie_showtime
    ON marquise.screenings(movie_id, showtime);

-- Account/key results and audit history survive Screening/Movie deletion.
-- No expiry or cascade FKs. Mutations, audit, and results commit together.
CREATE TABLE IF NOT EXISTS marquise.screening_write_results (
    account         TEXT NOT NULL,
    idempotency_key  TEXT NOT NULL,
    fingerprint     TEXT NOT NULL,
    result          JSONB NOT NULL,
    PRIMARY KEY (account, idempotency_key)
);

CREATE TABLE IF NOT EXISTS marquise.screening_write_audit (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    account         TEXT NOT NULL,
    idempotency_key  TEXT NOT NULL,
    operation       TEXT NOT NULL CHECK (operation IN ('create', 'update', 'delete')),
    target_id       TEXT NOT NULL,
    recorded_at     TIMESTAMPTZ NOT NULL,
    reason          TEXT NOT NULL,
    before_values   JSONB,
    after_values    JSONB,
    removed_movie   JSONB,
    UNIQUE (account, idempotency_key)
);

-- Restrict client access even if this schema is exposed through Supabase.
ALTER TABLE marquise.screening_write_results ENABLE ROW LEVEL SECURITY;
ALTER TABLE marquise.screening_write_audit ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON marquise.screening_write_results, marquise.screening_write_audit FROM PUBLIC;
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon') THEN
        REVOKE ALL ON marquise.screening_write_results, marquise.screening_write_audit FROM anon;
    END IF;
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN
        REVOKE ALL ON marquise.screening_write_results, marquise.screening_write_audit FROM authenticated;
    END IF;
END;
$$;
