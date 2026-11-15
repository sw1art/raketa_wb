"""Integration tests for listing read models (reservations, transfers)."""
from __future__ import annotations

from application.commands import (
    CreateTransferCommand,
    ItemLine,
    ReserveStockCommand,
)
from application.use_cases import CreateTransferUseCase, ReserveFBSStockUseCase
from infrastructure.repositories.unit_of_work import UnitOfWork

from .helpers import seed_catalog, set_stock


async def test_list_reservations_joined(session_factory):
    ids = await seed_catalog(session_factory)
    await set_stock(session_factory, ids["p101"], ids["north"], 20)

    async with session_factory() as session:
        await ReserveFBSStockUseCase().execute(
            UnitOfWork(session),
            ReserveStockCommand(warehouse_id=ids["north"], product_id=ids["p101"], quantity=5),
        )

    async with session_factory() as session:
        views = await UnitOfWork(session).reservations.list_joined(status="ACTIVE")
        assert len(views) == 1
        assert views[0].sku == "SKU-101"
        assert views[0].warehouse_name == "Север"
        assert views[0].quantity == 5


async def test_list_transfers_joined(session_factory):
    ids = await seed_catalog(session_factory)
    await set_stock(session_factory, ids["p101"], ids["north"], 10)

    async with session_factory() as session:
        await CreateTransferUseCase().execute(
            UnitOfWork(session),
            CreateTransferCommand(
                source_warehouse_id=ids["north"],
                target_warehouse_id=ids["south"],
                items=[ItemLine(product_id=ids["p101"], quantity=4)],
            ),
        )

    async with session_factory() as session:
        views = await UnitOfWork(session).transfers.list_joined(status="DRAFT")
        assert len(views) == 1
        assert views[0].source_warehouse_name == "Север"
        assert views[0].target_warehouse_name == "Юг"
        assert views[0].items[0].sku == "SKU-101"
        assert views[0].items[0].quantity == 4
