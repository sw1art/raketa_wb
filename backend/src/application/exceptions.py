"""Application exceptions mapped to HTTP status codes in presentation."""
from __future__ import annotations

from typing import Any


class AppError(Exception):
    status_code: int = 400
    code: str = "app_error"

    def __init__(self, message: str, *, detail: Any | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.detail = detail


class NotFoundError(AppError):
    status_code = 404
    code = "not_found"


class ValidationError(AppError):
    status_code = 422
    code = "validation_error"


class ConflictError(AppError):
    status_code = 409
    code = "conflict"


class InvalidStateError(ConflictError):
    code = "invalid_state"


class StockShortageError(ConflictError):
    code = "stock_shortage"

    def __init__(
        self,
        message: str,
        *,
        product_id: str,
        sku: str,
        warehouse_id: str,
        requested: int,
        available: int,
        shortfall: int,
        other_warehouses: list[dict[str, Any]],
    ) -> None:
        super().__init__(
            message,
            detail={
                "product_id": product_id,
                "sku": sku,
                "warehouse_id": warehouse_id,
                "requested": requested,
                "available": available,
                "shortfall": shortfall,
                "other_warehouses": other_warehouses,
                "suggestion": "create an internal transfer from a warehouse with available stock",
            },
        )


class WarehouseArchiveError(ConflictError):
    code = "warehouse_archive_error"

    def __init__(
        self,
        message: str,
        *,
        warehouse_id: str,
        reasons: list[str],
        nonzero_stocks: list[dict[str, Any]],
    ) -> None:
        super().__init__(
            message,
            detail={
                "warehouse_id": warehouse_id,
                "reasons": reasons,
                "nonzero_stocks": nonzero_stocks,
            },
        )


class IdempotencyConflictError(ConflictError):
    code = "idempotency_conflict"
