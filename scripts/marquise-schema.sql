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
    tmdb_id          TEXT UNIQUE,
    tmdb_rating      DOUBLE PRECISION,
    tmdb_vote_count  INTEGER,
    metadata_enriched_at TIMESTAMPTZ
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

-- Append one marker per movie/transaction without locking parent or counter rows.
-- Retain markers after deletion so a reference round trip cannot restore a revision.
CREATE TABLE IF NOT EXISTS marquise.movie_reference_revisions (
    movie_id TEXT NOT NULL,
    transaction_id BIGINT NOT NULL,
    PRIMARY KEY (movie_id, transaction_id)
);
ALTER TABLE marquise.movie_reference_revisions ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON marquise.movie_reference_revisions FROM PUBLIC;
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon') THEN
        REVOKE ALL ON marquise.movie_reference_revisions FROM anon;
    END IF;
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN
        REVOKE ALL ON marquise.movie_reference_revisions FROM authenticated;
    END IF;
END;
$$;

CREATE OR REPLACE FUNCTION marquise.advance_referenced_movie_revision()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
DECLARE
    old_id TEXT;
    new_id TEXT;
    target_id TEXT;
BEGIN
    IF TG_OP <> 'INSERT' THEN old_id := OLD.movie_id; END IF;
    IF TG_OP <> 'DELETE' THEN new_id := NEW.movie_id; END IF;
    FOR target_id IN
        SELECT DISTINCT id FROM unnest(ARRAY[old_id, new_id]) AS ids(id)
        WHERE id IS NOT NULL ORDER BY id
    LOOP
        INSERT INTO marquise.movie_reference_revisions (movie_id, transaction_id)
        VALUES (target_id, txid_current())
        ON CONFLICT (movie_id, transaction_id) DO NOTHING;
    END LOOP;
    RETURN NULL;
END;
$$;
DROP TRIGGER IF EXISTS screening_movie_metadata_revision ON marquise.screenings;
CREATE TRIGGER screening_movie_metadata_revision
AFTER INSERT OR UPDATE OR DELETE ON marquise.screenings
FOR EACH ROW EXECUTE FUNCTION marquise.advance_referenced_movie_revision();
