"""Tests for Price value object."""

from __future__ import annotations

import pytest

from marquise.domain.value_objects.price import Price


def test_price_creation() -> None:
    """Verify Price can be created with a float value."""
    price = Price(value=14.99)
    assert price.value == 14.99


def test_price_from_float() -> None:
    """Verify Price.from_float factory method works correctly."""
    price = Price.from_float(9.99)
    assert price.value == 9.99


def test_price_from_float_rejects_negative() -> None:
    """Verify Price.from_float rejects negative amounts."""
    with pytest.raises(ValueError, match="Price cannot be negative"):
        Price.from_float(-5.0)


def test_price_rejects_negative_direct_construction() -> None:
    """Verify Price rejects negative amounts via direct construction."""
    with pytest.raises(ValueError, match="Price cannot be negative"):
        Price(value=-5.0)


def test_price_str() -> None:
    """Verify the string representation is formatted to two decimal places."""
    price = Price(value=14.5)
    assert str(price) == "14.50"


def test_price_hash() -> None:
    """Verify Price hashing is based on value equality."""
    p1 = Price(value=10.0)
    p2 = Price(value=10.0)
    assert hash(p1) == hash(p2)


def test_price_hash_differs() -> None:
    """Verify that different prices produce different hashes."""
    p1 = Price(value=10.0)
    p2 = Price(value=20.0)
    assert hash(p1) != hash(p2)
