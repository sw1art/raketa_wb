"""Integration tests for the mandatory business scenarios (real PostgreSQL)."""

from __future__ import annotations

import asyncio

import pytest

from application.commands import (
    ArchiveWarehouseCommand,
    CancelReservationCommand,
    CreateFBOShipmentCommand,
    CreateTransferCommand,
    DispatchShipmentCommand,
    DispatchTransferCommand,
    ItemLine,
    ReceiveShipmentCommand,
    ReceiveStockCommand,
    ReceiveTransferCommand,
    ReserveStockCommand,
    ShipFBSCommand,
)
from application.exceptions import StockShortageError, WarehouseArchiveError
from application.use_cases import (
    ArchiveWarehouseUseCase,
    CancelFBSReservationUseCase,
    CreateFBOShipmentUseCase,
    CreateTransferUseCase,
    DispatchFBOShipmentUseCase,
    DispatchTransferUseCase,
    GetInTransitUseCase,
    ReceiveFBOShipmentUseCase,
    ReceiveStockUseCase,
    ReceiveTransferUseCase,
    ReserveFBSStockUseCase,
    ShipFBSOrderUseCase,
)
from domain.entities import Reservation
from infrastructure.repositories.unit_of_work import UnitOfWork

from .helpers import get_stock, seed_catalog, set_stock


async def _stock(session_factory, product_id, warehouse_id):
    return await get_stock(session_factory, product_id, warehouse_id)


async def test_scenario1_receipt(session_factory):
    ids = await seed_catalog(session_factory)
    await set_stock(session_factory, ids["p101"], ids["north"], 10)

    async with session_factory() as session:
        stock = await ReceiveStockUseCase().execute(
            UnitOfWork(session),
            ReceiveStockCommand(warehouse_id=ids["north"], product_id=ids["p101"], quantity=5),
        )
        assert stock.physical == 15

    persisted = await _stock(session_factory, ids["p101"], ids["north"])
    assert persisted.physical == 15


async def test_scenario2_reserve(session_factory):
    ids = await seed_catalog(session_factory)
    await set_stock(session_factory, ids["p101"], ids["north"], 20)

    async with session_factory() as session:
        await ReserveFBSStockUseCase().execute(
            UnitOfWork(session),
            ReserveStockCommand(warehouse_id=ids["north"], product_id=ids["p101"], quantity=5),
        )

    s = await _stock(session_factory, ids["p101"], ids["north"])
    assert (s.physical, s.reserved, s.available) == (20, 5, 15)


async def test_scenario3_cancel_reservation(session_factory):
    ids = await seed_catalog(session_factory)
    await set_stock(session_factory, ids["p101"], ids["north"], 20)

    async with session_factory() as session:
        reservation = await ReserveFBSStockUseCase().execute(
            UnitOfWork(session),
            ReserveStockCommand(warehouse_id=ids["north"], product_id=ids["p101"], quantity=5),
        )
    async with session_factory() as session:
        await CancelFBSReservationUseCase().execute(
            UnitOfWork(session), CancelReservationCommand(reservation_id=reservation.id)
        )

    s = await _stock(session_factory, ids["p101"], ids["north"])
    assert (s.physical, s.reserved, s.available) == (20, 0, 20)


async def test_scenario4_fbs_ship(session_factory):
    ids = await seed_catalog(session_factory)
    await set_stock(session_factory, ids["p101"], ids["north"], 20)

    async with session_factory() as session:
        reservation = await ReserveFBSStockUseCase().execute(
            UnitOfWork(session),
            ReserveStockCommand(warehouse_id=ids["north"], product_id=ids["p101"], quantity=5),
        )
    async with session_factory() as session:
        await ShipFBSOrderUseCase().execute(
            UnitOfWork(session), ShipFBSCommand(reservation_id=reservation.id)
        )

    s = await _stock(session_factory, ids["p101"], ids["north"])
    assert (s.physical, s.reserved, s.available) == (15, 0, 15)


async def test_scenario5_transfer(session_factory):
    ids = await seed_catalog(session_factory)
    await set_stock(session_factory, ids["p101"], ids["north"], 10)

    async with session_factory() as session:
        transfer = await CreateTransferUseCase().execute(
            UnitOfWork(session),
            CreateTransferCommand(
                source_warehouse_id=ids["north"],
                target_warehouse_id=ids["south"],
                items=[ItemLine(product_id=ids["p101"], quantity=4)],
            ),
        )

    async with session_factory() as session:
        await DispatchTransferUseCase().execute(
            UnitOfWork(session), DispatchTransferCommand(transfer_id=transfer.id)
        )
    north = await _stock(session_factory, ids["p101"], ids["north"])
    south = await _stock(session_factory, ids["p101"], ids["south"])
    assert north.physical == 6
    assert south is None or south.physical == 0

    async with session_factory() as session:
        transit = await GetInTransitUseCase().execute(UnitOfWork(session))
        row = next(r for r in transit["items"] if r["sku"] == "SKU-101")
        assert row["transfer"] == 4

    async with session_factory() as session:
        await ReceiveTransferUseCase().execute(
            UnitOfWork(session), ReceiveTransferCommand(transfer_id=transfer.id)
        )
    north = await _stock(session_factory, ids["p101"], ids["north"])
    south = await _stock(session_factory, ids["p101"], ids["south"])
    assert north.physical == 6
    assert south.physical == 4


async def test_scenario6_fbo(session_factory):
    ids = await seed_catalog(session_factory)
    await set_stock(session_factory, ids["p101"], ids["north"], 10)

    async with session_factory() as session:
        shipment = await CreateFBOShipmentUseCase().execute(
            UnitOfWork(session),
            CreateFBOShipmentCommand(
                source_warehouse_id=ids["north"],
                items=[ItemLine(product_id=ids["p101"], quantity=4)],
            ),
        )

    async with session_factory() as session:
        await DispatchFBOShipmentUseCase().execute(
            UnitOfWork(session), DispatchShipmentCommand(shipment_id=shipment.id)
        )
    north = await _stock(session_factory, ids["p101"], ids["north"])
    assert north.physical == 6

    async with session_factory() as session:
        await ReceiveFBOShipmentUseCase().execute(
            UnitOfWork(session), ReceiveShipmentCommand(shipment_id=shipment.id)
        )
    north = await _stock(session_factory, ids["p101"], ids["north"])
    assert north.physical == 6  # goods already left the warehouse


async def test_scenario7_shortage(session_factory):
    ids = await seed_catalog(session_factory)
    await set_stock(session_factory, ids["p101"], ids["north"], 2)
    await set_stock(session_factory, ids["p101"], ids["south"], 10)

    with pytest.raises(StockShortageError) as excinfo:
        async with session_factory() as session:
            await ReserveFBSStockUseCase().execute(
                UnitOfWork(session),
                ReserveStockCommand(warehouse_id=ids["north"], product_id=ids["p101"], quantity=5),
            )

    err = excinfo.value
    assert err.detail["shortfall"] == 3
    assert err.detail["available"] == 2
    assert any(
        w["warehouse_id"] == str(ids["south"]) and w["available"] == 10
        for w in err.detail["other_warehouses"]
    )
    # stock unchanged
    north = await _stock(session_factory, ids["p101"], ids["north"])
    assert north.physical == 2 and north.reserved == 0


async def test_scenario8_archive_blocked(session_factory):
    ids = await seed_catalog(session_factory)
    await set_stock(session_factory, ids["p101"], ids["north"], 10)

    with pytest.raises(WarehouseArchiveError) as excinfo:
        async with session_factory() as session:
            await ArchiveWarehouseUseCase().execute(
                UnitOfWork(session), ArchiveWarehouseCommand(warehouse_id=ids["north"])
            )

    err = excinfo.value
    assert any("non-zero" in r for r in err.detail["reasons"])
    assert err.detail["nonzero_stocks"][0]["sku"] == "SKU-101"
    north = await _stock(session_factory, ids["p101"], ids["north"])
    assert north.physical == 10


async def test_scenario9_double_confirm(session_factory):
    ids = await seed_catalog(session_factory)
    await set_stock(session_factory, ids["p101"], ids["north"], 20)

    async with session_factory() as session:
        reservation = await ReserveFBSStockUseCase().execute(
            UnitOfWork(session),
            ReserveStockCommand(warehouse_id=ids["north"], product_id=ids["p101"], quantity=5),
        )

    async with session_factory() as session:
        first = await ShipFBSOrderUseCase().execute(
            UnitOfWork(session), ShipFBSCommand(reservation_id=reservation.id)
        )
    async with session_factory() as session:
        second = await ShipFBSOrderUseCase().execute(
            UnitOfWork(session), ShipFBSCommand(reservation_id=reservation.id)
        )

    assert first.id == second.id  # idempotent: same shipment returned
    s = await _stock(session_factory, ids["p101"], ids["north"])
    assert (s.physical, s.reserved) == (15, 0)  # deducted exactly once


async def test_scenario10_concurrent(session_factory):
    ids = await seed_catalog(session_factory)
    await set_stock(session_factory, ids["p101"], ids["north"], 5)

    async def reserve(qty):
        async with session_factory() as session:
            return await ReserveFBSStockUseCase().execute(
                UnitOfWork(session),
                ReserveStockCommand(
                    warehouse_id=ids["north"], product_id=ids["p101"], quantity=qty
                ),
            )

    results = await asyncio.gather(reserve(3), reserve(3), return_exceptions=True)
    succeeded = [r for r in results if isinstance(r, Reservation)]
    failed = [r for r in results if isinstance(r, StockShortageError)]
    assert len(succeeded) == 1
    assert len(failed) == 1

    s = await _stock(session_factory, ids["p101"], ids["north"])
    assert s.physical == 5
    assert s.reserved == 3
    assert s.available == 2
