"""Warehouse (ФФ) use cases including archival."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from domain.entities import Warehouse
from domain.enums import OperationType
from domain.events import EVENT_WAREHOUSE_ARCHIVED, make_event
from domain.repositories.interfaces import UnitOfWork
from domain.services.archive import NonZeroStock, check_archive, check_purge

from ..commands import (
    ArchiveWarehouseCommand,
    CreateWarehouseCommand,
    PurgeWarehouseCommand,
    RenameWarehouseCommand,
)
from ..exceptions import (
    ConflictError,
    NotFoundError,
    WarehouseArchiveError,
    WarehousePurgeError,
)
from .base import UseCase, make_operation, new_id


class CreateWarehouseUseCase(UseCase):
    async def _run(self, uow: UnitOfWork, cmd: CreateWarehouseCommand) -> Warehouse:
        existing = await uow.warehouses.get_by_name(cmd.name)
        if existing is not None:
            raise ConflictError(f"warehouse '{cmd.name}' already exists")
        warehouse = Warehouse(id=new_id(), name=cmd.name, is_active=True)
        return await uow.warehouses.create(warehouse)


class RenameWarehouseUseCase(UseCase):
    async def _run(self, uow: UnitOfWork, cmd: RenameWarehouseCommand) -> Warehouse:
        warehouse = await uow.warehouses.get(cmd.warehouse_id)
        if warehouse is None:
            raise NotFoundError(f"warehouse {cmd.warehouse_id} not found")
        existing = await uow.warehouses.get_by_name(cmd.name)
        if existing is not None and existing.id != warehouse.id:
            raise ConflictError(f"warehouse '{cmd.name}' already exists")
        warehouse.name = cmd.name
        return await uow.warehouses.update(warehouse)


class GetWarehouseUseCase(UseCase):
    async def _run(self, uow: UnitOfWork, warehouse_id: UUID) -> Warehouse:
        warehouse = await uow.warehouses.get(warehouse_id)
        if warehouse is None:
            raise NotFoundError(f"warehouse {warehouse_id} not found")
        return warehouse


class ListWarehousesUseCase(UseCase):
    async def _run(self, uow: UnitOfWork, *, active_only: bool = False) -> list[Warehouse]:
        return await uow.warehouses.list(active_only=active_only)


class ArchiveWarehouseUseCase(UseCase):
    async def _run(self, uow: UnitOfWork, cmd: ArchiveWarehouseCommand) -> Warehouse:
        warehouse = await uow.warehouses.get(cmd.warehouse_id)
        if warehouse is None:
            raise NotFoundError(f"warehouse {cmd.warehouse_id} not found")
        if not warehouse.is_active:
            raise ConflictError(f"warehouse '{warehouse.name}' is already archived")

        nonzero = await uow.stocks.nonzero_by_warehouse(cmd.warehouse_id)
        nonzero_stocks = [
            NonZeroStock(
                product_id=stock.product_id,
                sku=product.sku,
                product_name=product.name,
                physical=stock.physical,
            )
            for stock, product in nonzero
            if stock.physical > 0
        ]
        open_transfers = await uow.transfers.count_open_by_warehouse(cmd.warehouse_id)
        open_shipments = await uow.shipments.count_open_by_warehouse(cmd.warehouse_id)
        active_reservations = await uow.reservations.count_active_by_warehouse(cmd.warehouse_id)

        check = check_archive(
            nonzero_stocks=nonzero_stocks,
            open_transfers=open_transfers,
            open_shipments=open_shipments,
            active_reservations=active_reservations,
        )
        if not check.allowed:
            raise WarehouseArchiveError(
                f"cannot archive warehouse '{warehouse.name}'",
                warehouse_id=str(cmd.warehouse_id),
                reasons=check.reasons,
                nonzero_stocks=[
                    {
                        "product_id": str(ns.product_id),
                        "sku": ns.sku,
                        "name": ns.product_name,
                        "physical": ns.physical,
                    }
                    for ns in check.nonzero_stocks
                ],
            )

        warehouse.is_active = False
        warehouse.archived_at = datetime.now(UTC)
        archived = await uow.warehouses.update(warehouse)

        # Запись об архивировании не должна ссылаться на склад через FK (иначе
        # архивный склад нельзя будет полностью удалить). Связь храним в entity_id.
        operation = make_operation(
            OperationType.WAREHOUSE_ARCHIVE,
            entity_type="warehouse",
            entity_id=cmd.warehouse_id,
        )
        await uow.operations.create(operation, [], [])
        await uow.outbox.add(
            make_event(
                EVENT_WAREHOUSE_ARCHIVED,
                aggregate_type="warehouse",
                aggregate_id=cmd.warehouse_id,
                data={"warehouse_id": str(cmd.warehouse_id), "name": warehouse.name},
            )
        )
        return archived


_REFERENCE_LABELS = {
    "stocks": "остатки",
    "reservations": "резервы",
    "transfers": "перемещения",
    "shipments": "отправки",
    "operations": "операции",
    "movements": "движения товара",
}


class PurgeWarehouseUseCase(UseCase):
    """Полное (физическое) удаление архивированного склада.

    Допустимо только если на склад ничего не ссылается — иначе будет нарушена
    сохранность истории операций и движений (обязательное требование ТЗ).
    """

    async def _run(self, uow: UnitOfWork, cmd: PurgeWarehouseCommand) -> Warehouse:
        warehouse = await uow.warehouses.get(cmd.warehouse_id)
        if warehouse is None:
            raise NotFoundError(f"warehouse {cmd.warehouse_id} not found")
        if warehouse.is_active:
            raise ConflictError(
                f"warehouse '{warehouse.name}' must be archived before full deletion"
            )

        references = await uow.warehouses.references(cmd.warehouse_id)
        check = check_purge(references)
        if not check.allowed:
            reasons = [
                f"{_REFERENCE_LABELS.get(name, name)}: {count}"
                for name, count in check.references.items()
            ]
            raise WarehousePurgeError(
                f"cannot delete warehouse '{warehouse.name}': history must be preserved",
                warehouse_id=str(cmd.warehouse_id),
                reasons=reasons,
                references=check.references,
            )

        await uow.warehouses.delete(cmd.warehouse_id)
        return warehouse
