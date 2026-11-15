"""Idempotent seed script — initial store, warehouses, products and stock."""
from __future__ import annotations

import asyncio
from uuid import uuid4

from config.logging import configure_logging
from config.settings import get_settings
from domain.entities import Product, Store, Warehouse
from infrastructure.database.session import SessionFactory, dispose_engine
from infrastructure.repositories.unit_of_work import UnitOfWork

STORE_NAME = "Ракета"
WAREHOUSES = ["Север", "Юг"]
PRODUCTS = [
    ("SKU-101", "Органайзер"),
    ("SKU-102", "Контейнер"),
    ("SKU-103", "Корзина"),
]
INITIAL_STOCK = {
    "SKU-101": {"Север": 10, "Юг": 6},
    "SKU-102": {"Север": 5, "Юг": 0},
    "SKU-103": {"Север": 0, "Юг": 4},
}


async def seed() -> None:
    async with SessionFactory() as session:
        uow = UnitOfWork(session)

        store = await uow.stores.get_default()
        if store is None:
            store = await uow.stores.create(Store(id=uuid4(), name=STORE_NAME))

        for name in WAREHOUSES:
            if await uow.warehouses.get_by_name(name) is None:
                await uow.warehouses.create(
                    Warehouse(id=uuid4(), name=name, is_active=True)
                )

        for sku, name in PRODUCTS:
            if await uow.products.get_by_sku(store.id, sku) is None:
                await uow.products.create(
                    Product(id=uuid4(), store_id=store.id, sku=sku, name=name)
                )

        await session.commit()

        warehouses = await uow.warehouses.list(active_only=False)
        wh_by_name = {w.name: w.id for w in warehouses}
        for sku, name in PRODUCTS:
            product = await uow.products.get_by_sku(store.id, sku)
            assert product is not None
            for wh_name, qty in INITIAL_STOCK[sku].items():
                wh_id = wh_by_name[wh_name]
                existing = await uow.stocks.get(product.id, wh_id)
                if existing is None:
                    stock = await uow.stocks.get_or_create_for_update(product.id, wh_id)
                    stock.physical = qty
                    stock.reserved = 0
                    await uow.stocks.save(stock)
        await session.commit()
        print(f"seed complete: store='{store.name}', "
              f"{len(WAREHOUSES)} warehouses, {len(PRODUCTS)} products")


def main() -> None:
    settings = get_settings()
    configure_logging(settings.log_level)
    asyncio.run(_run())


async def _run() -> None:
    try:
        await seed()
    finally:
        await dispose_engine()


if __name__ == "__main__":
    main()
