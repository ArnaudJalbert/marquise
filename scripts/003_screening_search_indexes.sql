-- Migration 003: Indexes supporting the screenings search/filter endpoints
-- Run this in the Supabase SQL Editor after migration 002.
--
-- The screenings table previously had no indexes beyond the primary key and
-- the (cinema_id, movie_id, showtime) / external_id unique constraints.
-- Those don't serve the new search patterns well: movie_id lookups alone,
-- and showtime range scans scoped to a single cinema or movie (the unique
-- index has movie_id between cinema_id and showtime, so it can't prune a
-- showtime range for a fixed cinema_id without touching every movie_id
-- bucket).

CREATE INDEX IF NOT EXISTS idx_screenings_movie_id
    ON marquise.screenings(movie_id);

CREATE INDEX IF NOT EXISTS idx_screenings_cinema_showtime
    ON marquise.screenings(cinema_id, showtime);

CREATE INDEX IF NOT EXISTS idx_screenings_movie_showtime
    ON marquise.screenings(movie_id, showtime);
