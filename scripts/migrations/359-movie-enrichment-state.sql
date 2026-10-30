-- Approved rollout only. Requires #321's tmdb_id column and unique index.
-- Existing identities remain pending. No enrichment or identity is inferred.
BEGIN;
SET LOCAL lock_timeout = '5s';
SET LOCAL statement_timeout = '60s';
ALTER TABLE marquise.movies
    ADD COLUMN IF NOT EXISTS metadata_enriched_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS metadata_revision BIGINT NOT NULL DEFAULT 0;

-- Advance on every movie write, including existing import paths.
CREATE OR REPLACE FUNCTION marquise.advance_movie_metadata_revision()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    NEW.metadata_revision := OLD.metadata_revision + 1;
    RETURN NEW;
END;
$$;
DROP TRIGGER IF EXISTS movie_metadata_revision ON marquise.movies;
CREATE TRIGGER movie_metadata_revision BEFORE UPDATE ON marquise.movies
FOR EACH ROW EXECUTE FUNCTION marquise.advance_movie_metadata_revision();

-- Reference edits must invalidate snapshots even after an insert/delete cycle.
CREATE OR REPLACE FUNCTION marquise.advance_referenced_movie_revision()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
DECLARE
    old_id TEXT;
    new_id TEXT;
    target_id TEXT;
BEGIN
    IF TG_OP <> 'INSERT' THEN old_id := OLD.movie_id; END IF;
    IF TG_OP <> 'DELETE' THEN new_id := NEW.movie_id; END IF;
    -- Stable lock order also covers a screening moved between two movies.
    FOR target_id IN
        SELECT DISTINCT id FROM unnest(ARRAY[old_id, new_id]) AS ids(id)
        WHERE id IS NOT NULL ORDER BY id
    LOOP
        UPDATE marquise.movies SET metadata_revision = metadata_revision + 1
        WHERE id = target_id;
    END LOOP;
    RETURN NULL;
END;
$$;
DROP TRIGGER IF EXISTS screening_movie_metadata_revision ON marquise.screenings;
CREATE TRIGGER screening_movie_metadata_revision
AFTER INSERT OR UPDATE OR DELETE ON marquise.screenings
FOR EACH ROW EXECUTE FUNCTION marquise.advance_referenced_movie_revision();
COMMIT;
