-- Migration 001: Initial Marquise database schema
-- Run this in the Supabase SQL Editor.
--
-- Creates all 5 tables with foreign key constraints and ON DELETE CASCADE.

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
    release_date     DATE,
    directors        TEXT,
    cast_members     TEXT,
    duration_minutes INTEGER,
    description      TEXT
);

CREATE TABLE IF NOT EXISTS marquise.screenings (
    id        TEXT PRIMARY KEY,
    movie_id  TEXT NOT NULL
        REFERENCES marquise.movies(id) ON DELETE CASCADE,
    cinema_id TEXT NOT NULL
        REFERENCES marquise.cinemas(id) ON DELETE CASCADE,
    showtime  TIMESTAMP NOT NULL,
    UNIQUE (cinema_id, movie_id, showtime)
);
