"""Application commands and queries (plain dataclasses)."""
from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID


@dataclass(frozen=True)
class CreateProductCommand:
    store_id: UUID | None = None
    sku: str = ""
    name: str = ""
    wb_external_id: str | None = None


@dataclass(frozen=True)
class UpdateProductCommand:
    product_id: UUID
    name: str | None = None
    sku: str | None = None
    wb_external_id: str | None = None


@dataclass(frozen=True)
class CreateWarehouseCommand:
    name: str


@dataclass(frozen=True)
class RenameWarehouseCommand:
    warehouse_id: UUID
    name: str


@dataclass(frozen=True)
class ArchiveWarehouseCommand:
    warehouse_id: UUID


@dataclass(frozen=True)
class ReceiveStockCommand:
    warehouse_id: UUID
    product_id: UUID
    quantity: int
    idempotency_key: str | None = None


@dataclass(frozen=True)
class ReserveStockCommand:
    warehouse_id: UUID
    product_id: UUID
    quantity: int
    idempotency_key: str | None = None


@dataclass(frozen=True)
class CancelReservationCommand:
    reservation_id: UUID


@dataclass(frozen=True)
class ShipFBSCommand:
    reservation_id: UUID
    idempotency_key: str | None = None


@dataclass(frozen=True)
class ItemLine:
    product_id: UUID
    quantity: int


@dataclass(frozen=True)
class CreateTransferCommand:
    source_warehouse_id: UUID
    target_warehouse_id: UUID
    items: list[ItemLine]
    idempotency_key: str | None = None


@dataclass(frozen=True)
class DispatchTransferCommand:
    transfer_id: UUID


@dataclass(frozen=True)
class ReceiveTransferCommand:
    transfer_id: UUID


@dataclass(frozen=True)
class CreateFBOShipmentCommand:
    source_warehouse_id: UUID
    items: list[ItemLine]
    idempotency_key: str | None = None


@dataclass(frozen=True)
class DispatchShipmentCommand:
    shipment_id: UUID


@dataclass(frozen=True)
class ReceiveShipmentCommand:
    shipment_id: UUID


@dataclass(frozen=True)
class ListQuery:
    offset: int = 0
    limit: int = 50
