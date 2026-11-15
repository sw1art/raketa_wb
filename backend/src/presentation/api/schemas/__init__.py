"""Request and response schemas (Pydantic v2)."""
from __future__ import annotations

from datetime import datetime
from typing import Generic, TypeVar
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


class ProductOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    store_id: UUID
    sku: str
    name: str
    wb_external_id: str | None = None


class WarehouseOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    name: str
    is_active: bool
    archived_at: datetime | None = None


class StockOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    product_id: UUID
    warehouse_id: UUID
    physical: int
    reserved: int
    available: int
    version: int


class ReservationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    product_id: UUID
    warehouse_id: UUID
    quantity: int
    status: str
    created_at: datetime | None = None
    cancelled_at: datetime | None = None
    shipped_at: datetime | None = None


class TransferItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    product_id: UUID
    quantity: int


class TransferOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    source_warehouse_id: UUID
    target_warehouse_id: UUID
    status: str
    items: list[TransferItemOut]
    created_at: datetime | None = None
    dispatched_at: datetime | None = None
    received_at: datetime | None = None


class ShipmentItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    product_id: UUID
    quantity: int


class ShipmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    type: str
    source_warehouse_id: UUID
    status: str
    destination: str | None = None
    external_status: str | None = None
    reservation_id: UUID | None = None
    items: list[ShipmentItemOut]
    created_at: datetime | None = None
    dispatched_at: datetime | None = None
    received_at: datetime | None = None


class HistoryEntryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    operation_id: UUID
    operation_type: str
    status: str
    created_at: datetime
    product_id: UUID | None = None
    sku: str | None = None
    product_name: str | None = None
    quantity: int
    source_warehouse_id: UUID | None = None
    source_warehouse_name: str | None = None
    target_warehouse_id: UUID | None = None
    target_warehouse_name: str | None = None
    related_entity_type: str | None = None
    related_entity_id: UUID | None = None


class WarehouseStockRow(BaseModel):
    warehouse_id: UUID
    warehouse_name: str
    physical: int
    reserved: int
    available: int


class StockRowOut(BaseModel):
    product_id: UUID
    sku: str
    name: str
    wb_external_id: str | None = None
    warehouses: list[WarehouseStockRow]
    total_physical: int
    total_reserved: int
    total_available: int
    in_transit: dict
    in_transit_total: int


class OverviewResponse(BaseModel):
    warehouses: list[WarehouseOut]
    products: list[StockRowOut]


class InTransitRow(BaseModel):
    product_id: UUID
    sku: str
    name: str
    transfer: int
    fbo: int
    fbs: int
    total: int


class InTransitResponse(BaseModel):
    items: list[InTransitRow]


class PaginatedProducts(BaseModel):
    items: list[ProductOut]
    total: int


class PaginatedHistory(BaseModel):
    items: list[HistoryEntryOut]
    total: int


class PaginatedShipments(BaseModel):
    items: list[ShipmentOut]
    total: int


class ReservationViewOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    product_id: UUID
    warehouse_id: UUID
    sku: str
    product_name: str
    warehouse_name: str
    quantity: int
    status: str
    created_at: datetime | None = None


class TransferItemViewOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    product_id: UUID
    sku: str
    quantity: int


class TransferViewOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    source_warehouse_id: UUID
    source_warehouse_name: str
    target_warehouse_id: UUID
    target_warehouse_name: str
    status: str
    items: list[TransferItemViewOut]
    created_at: datetime | None = None
    dispatched_at: datetime | None = None
    received_at: datetime | None = None


# ---- Requests ----
class ItemLine(BaseModel):
    product_id: UUID
    quantity: int = Field(gt=0)


class CreateProductRequest(BaseModel):
    sku: str = Field(min_length=1, max_length=128)
    name: str = Field(min_length=1, max_length=255)
    wb_external_id: str | None = None


class UpdateProductRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    sku: str | None = Field(default=None, min_length=1, max_length=128)
    wb_external_id: str | None = None


class CreateWarehouseRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)


class RenameWarehouseRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)


class ReceiveStockRequest(BaseModel):
    warehouse_id: UUID
    product_id: UUID
    quantity: int = Field(gt=0)


class ReserveStockRequest(BaseModel):
    warehouse_id: UUID
    product_id: UUID
    quantity: int = Field(gt=0)


class ShipFBSRequest(BaseModel):
    reservation_id: UUID


class CreateTransferRequest(BaseModel):
    source_warehouse_id: UUID
    target_warehouse_id: UUID
    items: list[ItemLine] = Field(min_length=1)


class CreateFBORequest(BaseModel):
    source_warehouse_id: UUID
    items: list[ItemLine] = Field(min_length=1)
