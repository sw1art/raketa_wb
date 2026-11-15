"""Unit tests for state-machine transition rules."""
from __future__ import annotations

import pytest

from domain.enums import ReservationStatus, ShipmentStatus, ShipmentType, TransferStatus
from domain.services.state_machine import (
    FBO_SHIPMENT_TRANSITIONS,
    FBS_SHIPMENT_TRANSITIONS,
    RESERVATION_TRANSITIONS,
    TRANSFER_TRANSITIONS,
    InvalidStateTransition,
    assert_transition,
    can_transition,
    shipment_transitions,
)


def test_reservation_transitions():
    assert can_transition(
        ReservationStatus.ACTIVE, ReservationStatus.CANCELLED, RESERVATION_TRANSITIONS
    )
    assert can_transition(
        ReservationStatus.ACTIVE, ReservationStatus.SHIPPED, RESERVATION_TRANSITIONS
    )
    assert not can_transition(
        ReservationStatus.CANCELLED, ReservationStatus.ACTIVE, RESERVATION_TRANSITIONS
    )
    assert not can_transition(
        ReservationStatus.SHIPPED, ReservationStatus.ACTIVE, RESERVATION_TRANSITIONS
    )


def test_transfer_transitions():
    assert can_transition(
        TransferStatus.DRAFT, TransferStatus.IN_TRANSIT, TRANSFER_TRANSITIONS
    )
    assert can_transition(
        TransferStatus.IN_TRANSIT, TransferStatus.RECEIVED, TRANSFER_TRANSITIONS
    )
    assert can_transition(
        TransferStatus.DRAFT, TransferStatus.CANCELLED, TRANSFER_TRANSITIONS
    )
    assert not can_transition(
        TransferStatus.IN_TRANSIT, TransferStatus.DRAFT, TRANSFER_TRANSITIONS
    )
    assert not can_transition(
        TransferStatus.RECEIVED, TransferStatus.IN_TRANSIT, TRANSFER_TRANSITIONS
    )


def test_shipment_transitions_per_type():
    assert shipment_transitions(ShipmentType.FBS) == FBS_SHIPMENT_TRANSITIONS
    assert shipment_transitions(ShipmentType.FBO) == FBO_SHIPMENT_TRANSITIONS


def test_fbs_shipment_transitions():
    assert can_transition(ShipmentStatus.DRAFT, ShipmentStatus.SHIPPED, FBS_SHIPMENT_TRANSITIONS)
    assert not can_transition(ShipmentStatus.DRAFT, ShipmentStatus.IN_TRANSIT, FBS_SHIPMENT_TRANSITIONS)


def test_fbo_shipment_transitions():
    assert can_transition(ShipmentStatus.DRAFT, ShipmentStatus.IN_TRANSIT, FBO_SHIPMENT_TRANSITIONS)
    assert can_transition(ShipmentStatus.IN_TRANSIT, ShipmentStatus.RECEIVED, FBO_SHIPMENT_TRANSITIONS)
    assert not can_transition(ShipmentStatus.RECEIVED, ShipmentStatus.IN_TRANSIT, FBO_SHIPMENT_TRANSITIONS)


def test_assert_transition_raises_on_invalid():
    with pytest.raises(InvalidStateTransition):
        assert_transition(TransferStatus.RECEIVED, TransferStatus.IN_TRANSIT, TRANSFER_TRANSITIONS)
