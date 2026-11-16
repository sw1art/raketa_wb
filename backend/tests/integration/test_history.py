"""Integration tests for the operations history (regression for the 500 bug)."""
from __future__ import annotations

from application.commands import ListQuery, ReceiveStockCommand, ReserveStockCommand
from application.use_cases import (
    GetHistoryUseCase,
    ListHistoryUseCase,
    ReceiveStockUseCase,
    ReserveFBSStockUseCase,
)
from infrastructure.repositories.unit_of_work import UnitOfWork

from .helpers import seed_catalog, set_stock


async def test_history_list_after_receipt(session_factory):
    ids = await seed_catalog(session_factory)
    await set_stock(session_factory, ids["p101"], ids["north"], 10)

    async with session_factory() as session:
        await ReceiveStockUseCase().execute(
            UnitOfWork(session),
            ReceiveStockCommand(warehouse_id=ids["north"], product_id=ids["p101"], quantity=5),
        )

    async with session_factory() as session:
        entries, total = await ListHistoryUseCase().execute(
            UnitOfWork(session), operation_type=None, sku=None, query=ListQuery(limit=50)
        )
    assert total >= 1
    receipt = [e for e in entries if e.operation_type == "RECEIPT"]
    assert len(receipt) == 1
    assert receipt[0].sku == "SKU-101"
    assert receipt[0].quantity == 5
    assert receipt[0].target_warehouse_name == "Север"


async def test_history_filter_by_operation_type(session_factory):
    ids = await seed_catalog(session_factory)
    await set_stock(session_factory, ids["p101"], ids["north"], 20)

    async with session_factory() as session:
        await ReserveFBSStockUseCase().execute(
            UnitOfWork(session),
            ReserveStockCommand(warehouse_id=ids["north"], product_id=ids["p101"], quantity=3),
        )

    async with session_factory() as session:
        entries, total = await ListHistoryUseCase().execute(
            UnitOfWork(session),
            operation_type="RESERVE",
            sku=None,
            query=ListQuery(limit=50),
        )
    assert total >= 1
    assert all(e.operation_type == "RESERVE" for e in entries)


async def test_get_history_detail(session_factory):
    ids = await seed_catalog(session_factory)
    await set_stock(session_factory, ids["p101"], ids["north"], 10)

    async with session_factory() as session:
        await ReceiveStockUseCase().execute(
            UnitOfWork(session),
            ReceiveStockCommand(warehouse_id=ids["north"], product_id=ids["p101"], quantity=2),
        )

    async with session_factory() as session:
        entries, _ = await ListHistoryUseCase().execute(
            UnitOfWork(session), operation_type=None, sku=None, query=ListQuery(limit=50)
        )
    operation_id = entries[0].operation_id

    async with session_factory() as session:
        detail = await GetHistoryUseCase().execute(UnitOfWork(session), operation_id)
    assert len(detail) == 1
    assert detail[0].operation_id == operation_id
