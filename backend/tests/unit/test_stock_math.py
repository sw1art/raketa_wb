"""Unit tests for pure stock arithmetic and invariants."""
from __future__ import annotations

import pytest

from domain.services.stock import (
    available,
    can_deduct,
    can_reserve,
    deduct,
    deduct_available,
    deduct_physical,
    receive,
    release,
    reserve,
    shortage,
)


def test_available_formula():
    assert available(20, 5) == 15
    assert available(10, 0) == 10


def test_reserve_keeps_physical():
    assert reserve(20, 0, 5) == (20, 5)


def test_reserve_insufficient_raises():
    with pytest.raises(ValueError):
        reserve(5, 0, 6)


def test_release():
    assert release(20, 5, 5) == (20, 0)


def test_release_more_than_reserved_raises():
    with pytest.raises(ValueError):
        release(20, 3, 5)


def test_deduct_shipped_reserved():
    # FBS: physical and reserved both decrease.
    assert deduct(20, 5, 5) == (15, 0)


def test_deduct_more_than_reserved_raises():
    with pytest.raises(ValueError):
        deduct(20, 3, 5)


def test_deduct_insufficient_physical_raises():
    with pytest.raises(ValueError):
        deduct(5, 5, 10)


def test_deduct_physical_unreserved():
    assert deduct_physical(10, 4) == 6


def test_deduct_available_for_transfer():
    # Transfer deducts available stock, reserved stays unchanged.
    assert deduct_available(10, 3, 4) == (6, 3)


def test_deduct_available_insufficient_raises():
    with pytest.raises(ValueError):
        deduct_available(10, 8, 3)  # available is only 2


def test_deduct_physical_insufficient_raises():
    with pytest.raises(ValueError):
        deduct_physical(3, 4)


def test_receive_increases():
    assert receive(10, 5) == 15


def test_can_deduct_boundaries():
    assert can_deduct(10, 3, 7) is True
    assert can_deduct(10, 3, 8) is False
    assert can_deduct(10, 3, 0) is True


def test_can_reserve_matches_available():
    assert can_reserve(10, 3, 7) is True
    assert can_reserve(10, 3, 8) is False


def test_shortage_computes_shortfall():
    s = shortage(2, 0, 5)
    assert s.requested == 5
    assert s.available == 2
    assert s.shortfall == 3
    assert s.exists is True


def test_no_shortage_when_enough():
    s = shortage(10, 0, 5)
    assert s.shortfall == 0
    assert s.exists is False
