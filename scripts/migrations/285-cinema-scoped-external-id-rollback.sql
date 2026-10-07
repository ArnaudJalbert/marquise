-- Refuses rollback if external IDs are shared across cinemas; never deletes rows.
-- On error, ROLLBACK before issuing any further statements in the same session.
BEGIN;
SET LOCAL lock_timeout = '5s';
SET LOCAL statement_timeout = '60s';

ALTER TABLE marquise.screenings
    DROP CONSTRAINT screenings_external_id_key,
    ADD CONSTRAINT screenings_external_id_key UNIQUE (external_id);

COMMIT;
