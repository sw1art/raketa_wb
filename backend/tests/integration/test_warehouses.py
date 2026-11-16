"""Integration tests for warehouse archival, name reuse and full deletion."""

from __future__ import annotations

import pytest

from application.commands import (
    ArchiveWarehouseCommand,
    CreateTransferCommand,
    CreateWarehouseCommand,
    DispatchTransferCommand,
    ItemLine,
    PurgeWarehouseCommand,
    ReceiveStockCommand,
    ReceiveTransferCommand,
)
from application.exceptions import ConflictError, WarehousePurgeError
from application.use_cases import (
    ArchiveWarehouseUseCase,
    CreateTransferUseCase,
    CreateWarehouseUseCase,
    DispatchTransferUseCase,
    PurgeWarehouseUseCase,
    ReceiveStockUseCase,
    ReceiveTransferUseCase,
)
from infrastructure.repositories.unit_of_work import UnitOfWork

from .helpers import seed_catalog


async def test_archive_empty_warehouse(session_factory):
    await seed_catalog(session_factory)
    async with session_factory() as session:
        uow = UnitOfWork(session)
        west = await CreateWarehouseUseCase().execute(uow, CreateWarehouseCommand(name="Запад"))

    async with session_factory() as session:
        uow = UnitOfWork(session)
        archived = await ArchiveWarehouseUseCase().execute(
            uow, ArchiveWarehouseCommand(warehouse_id=west.id)
        )
    assert archived.is_active is False


async def test_create_warehouse_reuses_archived_name(session_factory):
    await seed_catalog(session_factory)
    async with session_factory() as session:
        west = await CreateWarehouseUseCase().execute(
            UnitOfWork(session), CreateWarehouseCommand(name="Запад")
        )
    async with session_factory() as session:
        await ArchiveWarehouseUseCase().execute(
            UnitOfWork(session), ArchiveWarehouseCommand(warehouse_id=west.id)
        )

    # Имя архивированного склада можно использовать заново.
    async with session_factory() as session:
        west2 = await CreateWarehouseUseCase().execute(
            UnitOfWork(session), CreateWarehouseCommand(name="Запад")
        )
    assert west2.id != west.id
    assert west2.is_active is True


async def test_duplicate_active_warehouse_name_rejected(session_factory):
    await seed_catalog(session_factory)
    async with session_factory() as session:
        uow = UnitOfWork(session)
        await CreateWarehouseUseCase().execute(uow, CreateWarehouseCommand(name="Запад"))
        with pytest.raises(ConflictError):
            await CreateWarehouseUseCase().execute(uow, CreateWarehouseCommand(name="Запад"))


async def test_purge_unused_warehouse(session_factory):
    await seed_catalog(session_factory)
    async with session_factory() as session:
        west = await CreateWarehouseUseCase().execute(
            UnitOfWork(session), CreateWarehouseCommand(name="Запад")
        )
    async with session_factory() as session:
        await ArchiveWarehouseUseCase().execute(
            UnitOfWork(session), ArchiveWarehouseCommand(warehouse_id=west.id)
        )

    # Архивный склад без ссылок можно удалить полностью.
    async with session_factory() as session:
        await PurgeWarehouseUseCase().execute(
            UnitOfWork(session), PurgeWarehouseCommand(warehouse_id=west.id)
        )
    async with session_factory() as session:
        assert await UnitOfWork(session).warehouses.get(west.id) is None


async def test_purge_requires_archived(session_factory):
    ids = await seed_catalog(session_factory)
    async with session_factory() as session:
        with pytest.raises(ConflictError):
            await PurgeWarehouseUseCase().execute(
                UnitOfWork(session), PurgeWarehouseCommand(warehouse_id=ids["north"])
            )


async def test_purge_blocked_by_history(session_factory):
    ids = await seed_catalog(session_factory)
    async with session_factory() as session:
        west = await CreateWarehouseUseCase().execute(
            UnitOfWork(session), CreateWarehouseCommand(name="Запад")
        )

    # Склад использовался: приход 5 шт., затем полное перемещение на Север.
    async with session_factory() as session:
        await ReceiveStockUseCase().execute(
            UnitOfWork(session),
            ReceiveStockCommand(warehouse_id=west.id, product_id=ids["p101"], quantity=5),
        )
    async with session_factory() as session:
        transfer = await CreateTransferUseCase().execute(
            UnitOfWork(session),
            CreateTransferCommand(
                source_warehouse_id=west.id,
                target_warehouse_id=ids["north"],
                items=[ItemLine(product_id=ids["p101"], quantity=5)],
            ),
        )
    async with session_factory() as session:
        await DispatchTransferUseCase().execute(
            UnitOfWork(session), DispatchTransferCommand(transfer_id=transfer.id)
        )
    async with session_factory() as session:
        await ReceiveTransferUseCase().execute(
            UnitOfWork(session), ReceiveTransferCommand(transfer_id=transfer.id)
        )

    # Теперь Запад пуст и нет незавершённых операций — его можно архивировать.
    async with session_factory() as session:
        await ArchiveWarehouseUseCase().execute(
            UnitOfWork(session), ArchiveWarehouseCommand(warehouse_id=west.id)
        )

    # Но полное удаление запрещено: есть операции и движения (история сохраняется).
    async with session_factory() as session:
        with pytest.raises(WarehousePurgeError) as excinfo:
            await PurgeWarehouseUseCase().execute(
                UnitOfWork(session), PurgeWarehouseCommand(warehouse_id=west.id)
            )
    assert excinfo.value.detail["references"]
    assert excinfo.value.detail["reasons"]
