"""Unit tests for value objects."""

from __future__ import annotations

import pytest

from domain.value_objects import Quantity, Shortage


def test_quantity_rejects_negative():
    with pytest.raises(ValueError):
        Quantity(-1)


def test_quantity_allows_zero():
    assert Quantity(0).value == 0


def test_quantity_arithmetic():
    assert (Quantity(3) + Quantity(4)).value == 7
    assert (Quantity(5) - Quantity(2)).value == 3


def test_quantity_subtraction_negative_raises():
    with pytest.raises(ValueError):
        Quantity(2) - Quantity(5)


def test_shortage_shortfall():
    assert Shortage(requested=5, available=2).shortfall == 3
