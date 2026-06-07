"""Tests for CinemaId value object."""

from __future__ import annotations

from marquise.domain.value_objects.cinema_id import CinemaId


def test_cinema_id_creation() -> None:
    """Verify CinemaId can be created with a valid string value."""
    cid = CinemaId(value="cin-123")
    assert cid.value == "cin-123"


def test_cinema_id_str() -> None:
    """Verify CinemaId string representation matches the wrapped value."""
    cid = CinemaId(value="cin-123")
    assert str(cid) == "cin-123"


def test_cinema_id_hash() -> None:
    """Verify CinemaId hashing is based on value equality."""
    cid1 = CinemaId(value="cin-123")
    cid2 = CinemaId(value="cin-123")
    assert hash(cid1) == hash(cid2)


def test_cinema_id_hash_differs() -> None:
    """Verify that different values produce different hashes."""
    cid1 = CinemaId(value="cin-123")
    cid2 = CinemaId(value="cin-456")
    assert hash(cid1) != hash(cid2)
