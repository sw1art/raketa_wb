"""Domain entities — pure dataclasses, no ORM."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID

from ..enums import ReservationStatus, ShipmentStatus, ShipmentType, TransferStatus


@dataclass
class Store:
    id: UUID
    name: str


@dataclass
class Product:
    id: UUID
    store_id: UUID
    sku: str
    name: str
    wb_external_id: str | None = None


@dataclass
class Warehouse:
    id: UUID
    name: str
    is_active: bool = True
    archived_at: datetime | None = None


@dataclass
class Stock:
    product_id: UUID
    warehouse_id: UUID
    physical: int = 0
    reserved: int = 0
    version: int = 0

    def __post_init__(self) -> None:
        if self.physical < 0:
            raise ValueError("physical stock must be >= 0")
        if self.reserved < 0:
            raise ValueError("reserved stock must be >= 0")
        if self.reserved > self.physical:
            raise ValueError("reserved stock cannot exceed physical stock")

    @property
    def available(self) -> int:
        return self.physical - self.reserved


@dataclass
class Reservation:
    id: UUID
    product_id: UUID
    warehouse_id: UUID
    quantity: int
    status: ReservationStatus = ReservationStatus.ACTIVE
    operation_id: UUID | None = None
    created_at: datetime | None = None
    cancelled_at: datetime | None = None
    shipped_at: datetime | None = None


@dataclass
class TransferItem:
    product_id: UUID
    quantity: int


@dataclass
class Transfer:
    id: UUID
    source_warehouse_id: UUID
    target_warehouse_id: UUID
    status: TransferStatus = TransferStatus.DRAFT
    items: list[TransferItem] = field(default_factory=list)
    created_at: datetime | None = None
    dispatched_at: datetime | None = None
    received_at: datetime | None = None


@dataclass
class ShipmentItem:
    product_id: UUID
    quantity: int


@dataclass
class Shipment:
    id: UUID
    type: ShipmentType
    source_warehouse_id: UUID
    status: ShipmentStatus = ShipmentStatus.DRAFT
    destination: str | None = None
    external_status: str | None = None
    reservation_id: UUID | None = None
    items: list[ShipmentItem] = field(default_factory=list)
    created_at: datetime | None = None
    dispatched_at: datetime | None = None
    received_at: datetime | None = None


@dataclass
class Operation:
    id: UUID
    type: str
    status: str
    source_warehouse_id: UUID | None = None
    target_warehouse_id: UUID | None = None
    entity_type: str | None = None
    entity_id: UUID | None = None
    idempotency_key: str | None = None
    created_at: datetime | None = None


@dataclass
class OperationItem:
    product_id: UUID
    quantity: int
    source_warehouse_id: UUID | None = None
    target_warehouse_id: UUID | None = None


@dataclass
class StockMovement:
    product_id: UUID
    quantity: int
    movement_type: str
    source_warehouse_id: UUID | None = None
    target_warehouse_id: UUID | None = None
    operation_id: UUID | None = None
    created_at: datetime | None = None


@dataclass
class HistoryEntry:
    """Denormalized read model for the operations history screen."""

    operation_id: UUID
    operation_type: str
    status: str
    created_at: datetime
    product_id: UUID | None
    sku: str | None
    product_name: str | None
    quantity: int
    source_warehouse_id: UUID | None
    source_warehouse_name: str | None
    target_warehouse_id: UUID | None
    target_warehouse_name: str | None
    related_entity_type: str | None
    related_entity_id: UUID | None


@dataclass
class ReservationView:
    id: UUID
    product_id: UUID
    warehouse_id: UUID
    sku: str
    product_name: str
    warehouse_name: str
    quantity: int
    status: str
    created_at: datetime | None


@dataclass
class TransferItemView:
    product_id: UUID
    sku: str
    quantity: int


@dataclass
class TransferView:
    id: UUID
    source_warehouse_id: UUID
    source_warehouse_name: str
    target_warehouse_id: UUID
    target_warehouse_name: str
    status: str
    items: list[TransferItemView]
    created_at: datetime | None
    dispatched_at: datetime | None
    received_at: datetime | None
