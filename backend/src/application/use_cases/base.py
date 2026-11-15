"""Use-case base class and shared helpers."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from domain.entities import Operation, OperationItem, Product, StockMovement, Warehouse
from domain.repositories.interfaces import UnitOfWork

from ..exceptions import NotFoundError, StockShortageError


def now() -> datetime:
    return datetime.now(timezone.utc)


class UseCase:
    """Encapsulates the explicit transaction boundary around a use case."""

    async def execute(self, uow: UnitOfWork, *args: Any, **kwargs: Any) -> Any:
        try:
            result = await self._run(uow, *args, **kwargs)
            await uow.commit()
            return result
        except Exception:
            await uow.rollback()
            raise

    async def _run(self, uow: UnitOfWork, *args: Any, **kwargs: Any) -> Any:
        raise NotImplementedError


def new_id() -> UUID:
    return uuid4()


def make_operation(
    operation_type: str,
    *,
    source_warehouse_id: UUID | None = None,
    target_warehouse_id: UUID | None = None,
    entity_type: str | None = None,
    entity_id: UUID | None = None,
    idempotency_key: str | None = None,
) -> Operation:
    return Operation(
        id=new_id(),
        type=operation_type,
        status="SUCCESS",
        source_warehouse_id=source_warehouse_id,
        target_warehouse_id=target_warehouse_id,
        entity_type=entity_type,
        entity_id=entity_id,
        idempotency_key=idempotency_key,
        created_at=now(),
    )


def make_item(
    product_id: UUID,
    quantity: int,
    *,
    source_warehouse_id: UUID | None = None,
    target_warehouse_id: UUID | None = None,
) -> OperationItem:
    return OperationItem(
        product_id=product_id,
        quantity=quantity,
        source_warehouse_id=source_warehouse_id,
        target_warehouse_id=target_warehouse_id,
    )


def make_movement(
    product_id: UUID,
    quantity: int,
    movement_type: str,
    *,
    source_warehouse_id: UUID | None = None,
    target_warehouse_id: UUID | None = None,
    operation_id: UUID | None = None,
) -> StockMovement:
    return StockMovement(
        product_id=product_id,
        quantity=quantity,
        movement_type=movement_type,
        source_warehouse_id=source_warehouse_id,
        target_warehouse_id=target_warehouse_id,
        operation_id=operation_id,
        created_at=now(),
    )


async def get_product(uow: UnitOfWork, product_id: UUID) -> Product:
    product = await uow.products.get(product_id)
    if product is None:
        raise NotFoundError(f"product {product_id} not found")
    return product


async def get_warehouse(uow: UnitOfWork, warehouse_id: UUID) -> Warehouse:
    warehouse = await uow.warehouses.get(warehouse_id)
    if warehouse is None:
        raise NotFoundError(f"warehouse {warehouse_id} not found")
    return warehouse


async def raise_shortage(
    uow: UnitOfWork,
    product: Product,
    warehouse_id: UUID,
    requested: int,
    available: int,
) -> None:
    others = await uow.stocks.available_by_product(product.id, warehouse_id)
    other_warehouses = [
        {"warehouse_id": str(w.id), "name": w.name, "available": qty}
        for w, qty in others
        if qty > 0
    ]
    shortfall = max(0, requested - available)
    raise StockShortageError(
        f"insufficient stock for {product.sku}: requested {requested}, available {available}",
        product_id=str(product.id),
        sku=product.sku,
        warehouse_id=str(warehouse_id),
        requested=requested,
        available=available,
        shortfall=shortfall,
        other_warehouses=other_warehouses,
    )
