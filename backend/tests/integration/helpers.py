"""Test helpers for seeding catalog and stock."""

from __future__ import annotations

from uuid import UUID, uuid4

from domain.entities import Product, Store, Warehouse
from infrastructure.repositories.unit_of_work import UnitOfWork


async def seed_catalog(session_factory) -> dict[str, UUID]:
    async with session_factory() as session:
        uow = UnitOfWork(session)
        store = await uow.stores.create(Store(id=uuid4(), name="Ракета"))
        north = await uow.warehouses.create(Warehouse(id=uuid4(), name="Север", is_active=True))
        south = await uow.warehouses.create(Warehouse(id=uuid4(), name="Юг", is_active=True))
        products = {
            "p101": ("SKU-101", "Органайзер"),
            "p102": ("SKU-102", "Контейнер"),
            "p103": ("SKU-103", "Корзина"),
        }
        ids: dict[str, UUID] = {"store": store.id, "north": north.id, "south": south.id}
        for key, (sku, name) in products.items():
            product = await uow.products.create(
                Product(id=uuid4(), store_id=store.id, sku=sku, name=name)
            )
            ids[key] = product.id
        await session.commit()
        return ids


async def set_stock(
    session_factory,
    product_id: UUID,
    warehouse_id: UUID,
    physical: int,
    reserved: int = 0,
) -> None:
    async with session_factory() as session:
        uow = UnitOfWork(session)
        stock = await uow.stocks.get_or_create_for_update(product_id, warehouse_id)
        stock.physical = physical
        stock.reserved = reserved
        await uow.stocks.save(stock)
        await session.commit()


async def get_stock(session_factory, product_id: UUID, warehouse_id: UUID):
    async with session_factory() as session:
        uow = UnitOfWork(session)
        return await uow.stocks.get(product_id, warehouse_id)
