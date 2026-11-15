"""Domain services — re-exported for convenience."""
from .archive import ArchiveCheck, NonZeroStock, check_archive
from .state_machine import (
    FBO_SHIPMENT_TRANSITIONS,
    RESERVATION_TRANSITIONS,
    TRANSFER_TRANSITIONS,
    InvalidStateTransition,
    assert_transition,
    can_transition,
)
from .stock import (
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

__all__ = [
    "ArchiveCheck",
    "NonZeroStock",
    "check_archive",
    "FBO_SHIPMENT_TRANSITIONS",
    "RESERVATION_TRANSITIONS",
    "TRANSFER_TRANSITIONS",
    "InvalidStateTransition",
    "assert_transition",
    "can_transition",
    "available",
    "can_deduct",
    "can_reserve",
    "deduct",
    "deduct_available",
    "deduct_physical",
    "receive",
    "release",
    "reserve",
    "shortage",
]
