"""Domain enums: statuses, operation types, movement types."""

from __future__ import annotations

from enum import StrEnum


class OperationType(StrEnum):
    RECEIPT = "RECEIPT"
    RESERVE = "RESERVE"
    RESERVE_CANCEL = "RESERVE_CANCEL"
    FBS_SHIP = "FBS_SHIP"
    FBO_CREATE = "FBO_CREATE"
    FBO_DISPATCH = "FBO_DISPATCH"
    FBO_RECEIVE = "FBO_RECEIVE"
    TRANSFER_CREATE = "TRANSFER_CREATE"
    TRANSFER_DISPATCH = "TRANSFER_DISPATCH"
    TRANSFER_RECEIVE = "TRANSFER_RECEIVE"
    WAREHOUSE_ARCHIVE = "WAREHOUSE_ARCHIVE"


class MovementType(StrEnum):
    RECEIPT = "RECEIPT"
    FBS_SHIP = "FBS_SHIP"
    FBO_DISPATCH = "FBO_DISPATCH"
    TRANSFER_DISPATCH = "TRANSFER_DISPATCH"
    TRANSFER_RECEIVE = "TRANSFER_RECEIVE"


class ReservationStatus(StrEnum):
    ACTIVE = "ACTIVE"
    CANCELLED = "CANCELLED"
    SHIPPED = "SHIPPED"


class TransferStatus(StrEnum):
    DRAFT = "DRAFT"
    IN_TRANSIT = "IN_TRANSIT"
    RECEIVED = "RECEIVED"
    CANCELLED = "CANCELLED"


class ShipmentType(StrEnum):
    FBS = "FBS"
    FBO = "FBO"


class ShipmentStatus(StrEnum):
    DRAFT = "DRAFT"
    IN_TRANSIT = "IN_TRANSIT"
    SHIPPED = "SHIPPED"
    RECEIVED = "RECEIVED"
    CANCELLED = "CANCELLED"


class OutboxStatus(StrEnum):
    PENDING = "PENDING"
    PUBLISHED = "PUBLISHED"
    FAILED = "FAILED"


class WbSyncStatus(StrEnum):
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    DEMO = "DEMO"
