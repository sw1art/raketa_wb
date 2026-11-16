"""Integration tests for repository constraints and locking."""

from __future__ import annotations

from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError

from domain.entities import Product
from infrastructure.repositories.unit_of_work import UnitOfWork

from .helpers import seed_catalog, set_stock


async def test_duplicate_sku_rejected(session_factory):
    ids = await seed_catalog(session_factory)
    async with session_factory() as session:
        uow = UnitOfWork(session)
        with pytest.raises(IntegrityError):
            await uow.products.create(
                Product(id=uuid4(), store_id=ids["store"], sku="SKU-101", name="Дубль")
            )
            await uow.commit()


async def test_stock_get_or_create_is_idempotent(session_factory):
    ids = await seed_catalog(session_factory)
    async with session_factory() as session:
        uow = UnitOfWork(session)
        first = await uow.stocks.get_or_create_for_update(ids["p101"], ids["north"])
        second = await uow.stocks.get_or_create_for_update(ids["p101"], ids["north"])
        assert first.product_id == second.product_id
        assert first.warehouse_id == second.warehouse_id
        await uow.commit()


async def test_stock_negative_physical_rejected_by_db(session_factory):
    ids = await seed_catalog(session_factory)
    async with session_factory() as session:
        uow = UnitOfWork(session)
        stock = await uow.stocks.get_or_create_for_update(ids["p101"], ids["north"])
        stock.physical = -1
        with pytest.raises(IntegrityError):
            await uow.stocks.save(stock)
            await uow.commit()


async def test_reserved_cannot_exceed_physical(session_factory):
    ids = await seed_catalog(session_factory)
    await set_stock(session_factory, ids["p101"], ids["north"], physical=5)
    async with session_factory() as session:
        uow = UnitOfWork(session)
        stock = await uow.stocks.get_for_update(ids["p101"], ids["north"])
        stock.reserved = 6  # > physical 5
        with pytest.raises(IntegrityError):
            await uow.stocks.save(stock)
            await uow.commit()
