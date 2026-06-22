-- Migration 002: Add enriched movie fields and screening metadata
-- Run this in the Supabase SQL Editor after migration 001.

-- Movie enrichment fields
ALTER TABLE marquise.movies ADD COLUMN IF NOT EXISTS poster_url TEXT;
ALTER TABLE marquise.movies ADD COLUMN IF NOT EXISTS trailer_url TEXT;
ALTER TABLE marquise.movies ADD COLUMN IF NOT EXISTS genres TEXT;
ALTER TABLE marquise.movies ADD COLUMN IF NOT EXISTS original_title TEXT;
ALTER TABLE marquise.movies ADD COLUMN IF NOT EXISTS rating TEXT;
ALTER TABLE marquise.movies ADD COLUMN IF NOT EXISTS origin_countries TEXT;

-- Rename release_date to release_year and change type
ALTER TABLE marquise.movies ADD COLUMN IF NOT EXISTS release_year INTEGER;
UPDATE marquise.movies SET release_year = EXTRACT(YEAR FROM release_date) WHERE release_date IS NOT NULL;

-- Screening metadata fields
ALTER TABLE marquise.screenings ADD COLUMN IF NOT EXISTS external_id TEXT UNIQUE;
ALTER TABLE marquise.screenings ADD COLUMN IF NOT EXISTS ticket_url TEXT;
ALTER TABLE marquise.screenings ADD COLUMN IF NOT EXISTS room TEXT;
ALTER TABLE marquise.screenings ADD COLUMN IF NOT EXISTS language TEXT;
