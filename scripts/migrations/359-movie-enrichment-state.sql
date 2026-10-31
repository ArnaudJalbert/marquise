-- Approved rollout only. Requires #321's tmdb_id column and unique index.
-- Existing identities remain pending. No enrichment or identity is inferred.
BEGIN;
SET LOCAL lock_timeout = '5s';
SET LOCAL statement_timeout = '60s';
ALTER TABLE marquise.movies
    ADD COLUMN IF NOT EXISTS metadata_enriched_at TIMESTAMPTZ;


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
COMMIT;
