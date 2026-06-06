"""Tests for ScreeningId value object."""

from __future__ import annotations

from marquise.domain.value_objects.screening_id import ScreeningId


def test_screening_id_str() -> None:
    sid = ScreeningId(value="scr-123")
    assert str(sid) == "scr-123"


def test_screening_id_hash() -> None:
    sid1 = ScreeningId(value="scr-123")
    sid2 = ScreeningId(value="scr-123")
    assert hash(sid1) == hash(sid2)


def test_screening_id_hash_differs() -> None:
    sid1 = ScreeningId(value="scr-123")
    sid2 = ScreeningId(value="scr-456")
    assert hash(sid1) != hash(sid2)
