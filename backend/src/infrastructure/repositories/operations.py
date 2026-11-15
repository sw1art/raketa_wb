"""Operation (audit) and Outbox repositories."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from domain.entities import HistoryEntry, Operation, OperationItem, StockMovement
from domain.enums import OutboxStatus
from domain.events import DomainEvent
from infrastructure.database.models import Operation as OperationModel
from infrastructure.database.models import OperationItem as OperationItemModel
from infrastructure.database.models import OutboxEvent as OutboxEventModel
from infrastructure.database.models import Product as ProductModel
from infrastructure.database.models import StockMovement as StockMovementModel
from infrastructure.database.models import Warehouse as WarehouseModel

_SOURCE_WH = aliased(WarehouseModel)
_TARGET_WH = aliased(WarehouseModel)


def _operation_to_domain(op: OperationModel) -> Operation:
    return Operation(
        id=op.id,
        type=op.type,
        status=op.status,
        source_warehouse_id=op.source_warehouse_id,
        target_warehouse_id=op.target_warehouse_id,
        entity_type=op.entity_type,
        entity_id=op.entity_id,
        idempotency_key=op.idempotency_key,
        created_at=op.created_at,
    )


def _history_entry(
    op: OperationModel, item: OperationItemModel, product: ProductModel, src, dst
) -> HistoryEntry:
    return HistoryEntry(
        operation_id=op.id,
        operation_type=op.type.value if hasattr(op.type, "value") else str(op.type),
        status=op.status,
        created_at=op.created_at,
        product_id=product.id if product else None,
        sku=product.sku if product else None,
        product_name=product.name if product else None,
        quantity=item.quantity,
        source_warehouse_id=item.source_warehouse_id,
        source_warehouse_name=src.name if src else None,
        target_warehouse_id=item.target_warehouse_id,
        target_warehouse_name=dst.name if dst else None,
        related_entity_type=op.entity_type,
        related_entity_id=op.entity_id,
    )


class OperationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        operation: Operation,
        items: list[OperationItem],
        movements: list[StockMovement],
    ) -> Operation:
        op_model = OperationModel(
            id=operation.id,
            type=operation.type,
            status=operation.status,
            source_warehouse_id=operation.source_warehouse_id,
            target_warehouse_id=operation.target_warehouse_id,
            entity_type=operation.entity_type,
            entity_id=operation.entity_id,
            idempotency_key=operation.idempotency_key,
            created_at=operation.created_at,
        )
        self._session.add(op_model)
        for item in items:
            self._session.add(
                OperationItemModel(
                    operation_id=operation.id,
                    product_id=item.product_id,
                    quantity=item.quantity,
                    source_warehouse_id=item.source_warehouse_id,
                    target_warehouse_id=item.target_warehouse_id,
                )
            )
        for movement in movements:
            self._session.add(
                StockMovementModel(
                    product_id=movement.product_id,
                    quantity=movement.quantity,
                    movement_type=movement.movement_type,
                    source_warehouse_id=movement.source_warehouse_id,
                    target_warehouse_id=movement.target_warehouse_id,
                    operation_id=movement.operation_id,
                    created_at=movement.created_at,
                )
            )
        await self._session.flush()
        return operation

    async def get(self, operation_id: UUID) -> Operation | None:
        model = await self._session.get(OperationModel, operation_id)
        return _operation_to_domain(model) if model else None

    async def get_by_idempotency_key(self, key: str) -> Operation | None:
        model = await self._session.scalar(
            select(OperationModel).where(OperationModel.idempotency_key == key)
        )
        return _operation_to_domain(model) if model else None

    async def _history_query(self):
        return (
            select(OperationModel, OperationItemModel, ProductModel, _SOURCE_WH, _TARGET_WH)
            .join(OperationItemModel, OperationItemModel.operation_id == OperationModel.id)
            .join(ProductModel, ProductModel.id == OperationItemModel.product_id)
            .outerjoin(_SOURCE_WH, _SOURCE_WH.id == OperationItemModel.source_warehouse_id)
            .outerjoin(_TARGET_WH, _TARGET_WH.id == OperationItemModel.target_warehouse_id)
        )

    async def list_history(
        self,
        *,
        operation_type: str | None,
        sku: str | None,
        offset: int,
        limit: int,
    ) -> tuple[list[HistoryEntry], int]:
        conditions = []
        if operation_type:
            conditions.append(OperationModel.type == operation_type)
        if sku:
            conditions.append(ProductModel.sku.ilike(f"%{sku}%"))

        total = await self._session.scalar(
            select(func.count(func.distinct(OperationModel.id)))
            .select_from(OperationModel)
            .join(OperationItemModel, OperationItemModel.operation_id == OperationModel.id)
            .join(ProductModel, ProductModel.id == OperationItemModel.product_id)
            .where(*conditions)
        )

        stmt = self._history_query().where(*conditions)
        stmt = stmt.order_by(OperationModel.created_at.desc(), OperationModel.id)
        rows = await self._session.execute(stmt.offset(offset).limit(limit))
        entries = [
            _history_entry(op, item, product, src, dst) for op, item, product, src, dst in rows
        ]
        return entries, int(total or 0)

    async def get_history(self, operation_id: UUID) -> list[HistoryEntry]:
        stmt = self._history_query().where(OperationModel.id == operation_id)
        stmt = stmt.order_by(OperationItemModel.id)
        rows = await self._session.execute(stmt)
        return [_history_entry(op, item, product, src, dst) for op, item, product, src, dst in rows]


class OutboxRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, event: DomainEvent) -> None:
        model = OutboxEventModel(
            event_id=event.event_id,
            aggregate_type=event.aggregate_type,
            aggregate_id=event.aggregate_id,
            event_type=event.event_type,
            payload=event.to_dict(),
            version=event.version,
            status=OutboxStatus.PENDING,
        )
        self._session.add(model)
        await self._session.flush()
