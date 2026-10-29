-- Apply before deploying code that reads movies.tmdb_id. Existing rows stay NULL.
-- A unique index prevents concurrent imports from creating two movies for one TMDB id.
BEGIN;
SET LOCAL lock_timeout = '5s';
SET LOCAL statement_timeout = '60s';
ALTER TABLE marquise.movies ADD COLUMN IF NOT EXISTS tmdb_id TEXT;
CREATE UNIQUE INDEX IF NOT EXISTS movies_tmdb_id_key ON marquise.movies (tmdb_id);
COMMIT;
