"""Import all ORM models so Alembic autogenerate and metadata see them."""

from .base import Base
from .catalog import Product, Stock, Store, Warehouse
from .events import OutboxEvent, ProcessedEvent
from .integrations import WbSyncLog
from .operations import Operation, OperationItem, StockMovement
from .warehouse_ops import (
    Reservation,
    Shipment,
    ShipmentItem,
    Transfer,
    TransferItem,
)

__all__ = [
    "Base",
    "Operation",
    "OperationItem",
    "OutboxEvent",
    "ProcessedEvent",
    "Product",
    "Reservation",
    "Shipment",
    "ShipmentItem",
    "Stock",
    "StockMovement",
    "Store",
    "Transfer",
    "TransferItem",
    "Warehouse",
    "WbSyncLog",
]
