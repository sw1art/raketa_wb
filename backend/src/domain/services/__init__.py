"""Domain services — re-exported for convenience."""

from .archive import ArchiveCheck, NonZeroStock, PurgeCheck, check_archive, check_purge
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
    "FBO_SHIPMENT_TRANSITIONS",
    "RESERVATION_TRANSITIONS",
    "TRANSFER_TRANSITIONS",
    "ArchiveCheck",
    "InvalidStateTransition",
    "NonZeroStock",
    "PurgeCheck",
    "assert_transition",
    "available",
    "can_deduct",
    "can_reserve",
    "can_transition",
    "check_archive",
    "check_purge",
    "deduct",
    "deduct_available",
    "deduct_physical",
    "receive",
    "release",
    "reserve",
    "shortage",
]
