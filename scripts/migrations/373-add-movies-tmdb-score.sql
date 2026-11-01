-- Apply before deploying code that reads or writes TMDB scores.
-- Existing movies retain NULL scores until enrichment fetches them.
BEGIN;
SET LOCAL lock_timeout = '5s';
SET LOCAL statement_timeout = '60s';
ALTER TABLE marquise.movies
    ADD COLUMN IF NOT EXISTS tmdb_rating DOUBLE PRECISION,
    ADD COLUMN IF NOT EXISTS tmdb_vote_count INTEGER;
COMMIT;
