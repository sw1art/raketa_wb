"""Pure stock arithmetic and invariant checks.

All functions are side-effect free and unit-testable without a database.
"""
from __future__ import annotations

from ..value_objects import Shortage


def available(physical: int, reserved: int) -> int:
    """Available = Physical - Reserved."""
    return physical - reserved


def can_deduct(physical: int, reserved: int, quantity: int) -> bool:
    """Whether `quantity` can be deducted without going negative."""
    return quantity >= 0 and available(physical, reserved) >= quantity


def can_reserve(physical: int, reserved: int, quantity: int) -> bool:
    """Reserving consumes available stock (Reserved <= Physical must hold)."""
    return can_deduct(physical, reserved, quantity)


def reserve(physical: int, reserved: int, quantity: int) -> tuple[int, int]:
    """Reserve `quantity`: physical unchanged, reserved increased."""
    if not can_reserve(physical, reserved, quantity):
        raise ValueError("insufficient available stock")
    return physical, reserved + quantity


def release(physical: int, reserved: int, quantity: int) -> tuple[int, int]:
    """Release `quantity` of reserved stock; physical unchanged."""
    if quantity > reserved:
        raise ValueError("cannot release more than reserved")
    return physical, reserved - quantity


def deduct(physical: int, reserved: int, quantity: int) -> tuple[int, int]:
    """Deduct `quantity` from physical; reserved must already cover it.

    Returns (new_physical, new_reserved). Physical and reserved are both reduced
    when shipping an already-reserved quantity.
    """
    if not can_deduct(physical, reserved, quantity):
        raise ValueError("insufficient physical stock")
    if quantity > reserved:
        raise ValueError("cannot deduct more than reserved quantity")
    return physical - quantity, reserved - quantity


def deduct_physical(physical: int, quantity: int) -> int:
    """Deduct from physical only (unreserved stock, e.g. FBO dispatch)."""
    if quantity > physical:
        raise ValueError("insufficient physical stock")
    return physical - quantity


def deduct_available(physical: int, reserved: int, quantity: int) -> tuple[int, int]:
    """Deduct from available stock (internal transfers).

    Physical decreases, reserved stays unchanged.
    """
    if not can_deduct(physical, reserved, quantity):
        raise ValueError("insufficient available stock")
    return physical - quantity, reserved


def receive(physical: int, quantity: int) -> int:
    """Increase physical by `quantity` (receipt / transfer receive)."""
    return physical + quantity


def shortage(physical: int, reserved: int, quantity: int) -> Shortage:
    return Shortage(requested=quantity, available=available(physical, reserved))
