"""Tests for Price value object."""

from __future__ import annotations

import pytest

from marquise.domain.value_objects.price import Price


def test_price_creation() -> None:
    price = Price(value=14.99)
    assert price.value == 14.99


def test_price_from_float() -> None:
    price = Price.from_float(9.99)
    assert price.value == 9.99


def test_price_from_float_rejects_negative() -> None:
    with pytest.raises(ValueError, match="Price cannot be negative"):
        Price.from_float(-5.0)


def test_price_str() -> None:
    price = Price(value=14.5)
    assert str(price) == "14.50"


def test_price_hash() -> None:
    p1 = Price(value=10.0)
    p2 = Price(value=10.0)
    assert hash(p1) == hash(p2)


def test_price_hash_differs() -> None:
    p1 = Price(value=10.0)
    p2 = Price(value=20.0)
    assert hash(p1) != hash(p2)
