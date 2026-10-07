-- Run during a quiet import window, after explicit live-rollout approval.
-- Existing rows remain source-unknown and cannot trigger guarded reschedules.
BEGIN;
SET LOCAL lock_timeout = '5s';
SET LOCAL statement_timeout = '60s';

ALTER TABLE marquise.screenings
    ADD COLUMN IF NOT EXISTS source_name TEXT
        REFERENCES marquise.source_definitions(name) ON DELETE SET NULL;

COMMIT;
