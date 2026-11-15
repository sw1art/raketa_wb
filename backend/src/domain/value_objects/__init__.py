"""Domain value objects."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, order=True)
class Quantity:
    """Non-negative integer quantity. Encapsulates the core non-negativity invariant."""

    value: int

    def __post_init__(self) -> None:
        if not isinstance(self.value, int) or isinstance(self.value, bool):
            raise ValueError("quantity must be an integer")
        if self.value < 0:
            raise ValueError("quantity must be non-negative")

    def __add__(self, other: Quantity) -> Quantity:
        return Quantity(self.value + other.value)

    def __sub__(self, other: Quantity) -> Quantity:
        result = self.value - other.value
        if result < 0:
            raise ValueError("quantity cannot become negative")
        return Quantity(result)

    def __int__(self) -> int:
        return self.value


@dataclass(frozen=True)
class Shortage:
    """Structured description of a stock shortage."""

    requested: int
    available: int

    @property
    def shortfall(self) -> int:
        return max(0, self.requested - self.available)

    @property
    def exists(self) -> bool:
        return self.shortfall > 0
