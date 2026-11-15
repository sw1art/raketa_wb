"""State-machine transition rules."""
from __future__ import annotations

from typing import Mapping, TypeAlias

from ..enums import (
    ReservationStatus,
    ShipmentStatus,
    ShipmentType,
    TransferStatus,
)

Transitions: TypeAlias = Mapping[object, set[object]]

RESERVATION_TRANSITIONS: dict[ReservationStatus, set[ReservationStatus]] = {
    ReservationStatus.ACTIVE: {ReservationStatus.CANCELLED, ReservationStatus.SHIPPED},
}

TRANSFER_TRANSITIONS: dict[TransferStatus, set[TransferStatus]] = {
    TransferStatus.DRAFT: {TransferStatus.IN_TRANSIT, TransferStatus.CANCELLED},
    TransferStatus.IN_TRANSIT: {TransferStatus.RECEIVED},
}

FBS_SHIPMENT_TRANSITIONS: dict[ShipmentStatus, set[ShipmentStatus]] = {
    ShipmentStatus.DRAFT: {ShipmentStatus.SHIPPED, ShipmentStatus.CANCELLED},
}

FBO_SHIPMENT_TRANSITIONS: dict[ShipmentStatus, set[ShipmentStatus]] = {
    ShipmentStatus.DRAFT: {ShipmentStatus.IN_TRANSIT, ShipmentStatus.CANCELLED},
    ShipmentStatus.IN_TRANSIT: {ShipmentStatus.RECEIVED},
}


class InvalidStateTransition(Exception):
    def __init__(self, current: object, target: object) -> None:
        super().__init__(f"invalid state transition: {current} -> {target}")
        self.current = current
        self.target = target


def shipment_transitions(shipment_type: ShipmentType) -> dict[ShipmentStatus, set[ShipmentStatus]]:
    if shipment_type is ShipmentType.FBS:
        return FBS_SHIPMENT_TRANSITIONS
    return FBO_SHIPMENT_TRANSITIONS


def can_transition(
    current: object,
    target: object,
    transitions: Mapping[object, set[object]],
) -> bool:
    return target in transitions.get(current, set())


def assert_transition(
    current: object,
    target: object,
    transitions: Mapping[object, set[object]],
) -> None:
    if not can_transition(current, target, transitions):
        raise InvalidStateTransition(current, target)
