"""Domain events."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

EVENT_STOCK_RECEIVED = "StockReceived"
EVENT_STOCK_RESERVED = "StockReserved"
EVENT_STOCK_RESERVATION_CANCELLED = "StockReservationCancelled"
EVENT_FBS_ORDER_SHIPPED = "FBSOrderShipped"
EVENT_FBO_SHIPMENT_CREATED = "FBOShipmentCreated"
EVENT_FBO_SHIPMENT_DISPATCHED = "FBOShipmentDispatched"
EVENT_FBO_SHIPMENT_RECEIVED = "FBOShipmentReceived"
EVENT_TRANSFER_CREATED = "TransferCreated"
EVENT_TRANSFER_DISPATCHED = "TransferDispatched"
EVENT_TRANSFER_RECEIVED = "TransferReceived"
EVENT_WAREHOUSE_ARCHIVED = "WarehouseArchived"


@dataclass(frozen=True)
class DomainEvent:
    event_type: str
    aggregate_type: str
    aggregate_id: UUID
    data: dict[str, Any] = field(default_factory=dict)
    version: int = 1
    event_id: UUID = field(default_factory=uuid4)
    occurred_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": str(self.event_id),
            "event_type": self.event_type,
            "event_version": self.version,
            "aggregate_type": self.aggregate_type,
            "aggregate_id": str(self.aggregate_id),
            "occurred_at": self.occurred_at.isoformat(),
            "data": self.data,
        }


def make_event(
    event_type: str,
    aggregate_type: str,
    aggregate_id: UUID,
    data: dict[str, Any],
) -> DomainEvent:
    return DomainEvent(
        event_type=event_type,
        aggregate_type=aggregate_type,
        aggregate_id=aggregate_id,
        data=data,
    )
