"""Tests for MovieId value object."""

from __future__ import annotations

from marquise.domain.value_objects.movie_id import MovieId


def test_movie_id_creation() -> None:
    """Verify MovieId can be created with a valid string value."""
    mid = MovieId(value="mov-123")
    assert mid.value == "mov-123"


def test_movie_id_str() -> None:
    """Verify MovieId string representation matches the wrapped value."""
    mid = MovieId(value="mov-123")
    assert str(mid) == "mov-123"


def test_movie_id_hash() -> None:
    """Verify MovieId hashing is based on value equality."""
    mid1 = MovieId(value="mov-123")
    mid2 = MovieId(value="mov-123")
    assert hash(mid1) == hash(mid2)


def test_movie_id_hash_differs() -> None:
    """Verify that different values produce different hashes."""
    mid1 = MovieId(value="mov-123")
    mid2 = MovieId(value="mov-456")
    assert hash(mid1) != hash(mid2)
