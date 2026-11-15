"""Product catalog use cases."""

from __future__ import annotations

from uuid import UUID

from domain.entities import Product, Store
from domain.repositories.interfaces import UnitOfWork

from ..commands import CreateProductCommand, ListQuery, UpdateProductCommand
from ..exceptions import ConflictError, NotFoundError
from .base import UseCase, new_id


class CreateProductUseCase(UseCase):
    async def _run(self, uow: UnitOfWork, cmd: CreateProductCommand) -> Product:
        store_id = cmd.store_id
        if store_id is None:
            store = await uow.stores.get_default()
            if store is None:
                raise NotFoundError("no store exists; run the seed script first")
            store_id = store.id
        else:
            store = await uow.stores.get(store_id)
            if store is None:
                raise NotFoundError(f"store {store_id} not found")
        existing = await uow.products.get_by_sku(store_id, cmd.sku)
        if existing is not None:
            raise ConflictError(f"SKU '{cmd.sku}' already exists in this store")
        product = Product(
            id=new_id(),
            store_id=store_id,
            sku=cmd.sku,
            name=cmd.name,
            wb_external_id=cmd.wb_external_id,
        )
        return await uow.products.create(product)


class UpdateProductUseCase(UseCase):
    async def _run(self, uow: UnitOfWork, cmd: UpdateProductCommand) -> Product:
        product = await uow.products.get(cmd.product_id)
        if product is None:
            raise NotFoundError(f"product {cmd.product_id} not found")
        if cmd.sku is not None and cmd.sku != product.sku:
            existing = await uow.products.get_by_sku(product.store_id, cmd.sku)
            if existing is not None and existing.id != product.id:
                raise ConflictError(f"SKU '{cmd.sku}' already exists in this store")
            product.sku = cmd.sku
        if cmd.name is not None:
            product.name = cmd.name
        if cmd.wb_external_id is not None:
            product.wb_external_id = cmd.wb_external_id
        return await uow.products.update(product)


class GetProductUseCase(UseCase):
    async def _run(self, uow: UnitOfWork, product_id: UUID) -> Product:
        product = await uow.products.get(product_id)
        if product is None:
            raise NotFoundError(f"product {product_id} not found")
        return product


class ListProductsUseCase(UseCase):
    async def _run(
        self,
        uow: UnitOfWork,
        *,
        sku: str | None = None,
        name: str | None = None,
        query: ListQuery,
    ) -> tuple[list[Product], int]:
        return await uow.products.list(sku=sku, name=name, offset=query.offset, limit=query.limit)


class CreateStoreUseCase(UseCase):
    async def _run(self, uow: UnitOfWork, name: str) -> Store:
        store = Store(id=new_id(), name=name)
        return await uow.stores.create(store)
