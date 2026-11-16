"""Catalog repositories: Store, Product, Warehouse, Stock."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import delete, func, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from domain.entities import Product, Stock, Store, Warehouse
from infrastructure.database.models import Operation as OperationModel
from infrastructure.database.models import Product as ProductModel
from infrastructure.database.models import Reservation as ReservationModel
from infrastructure.database.models import Shipment as ShipmentModel
from infrastructure.database.models import Stock as StockModel
from infrastructure.database.models import StockMovement as StockMovementModel
from infrastructure.database.models import Store as StoreModel
from infrastructure.database.models import Transfer as TransferModel
from infrastructure.database.models import Warehouse as WarehouseModel


def _stock_to_domain(s: StockModel) -> Stock:
    return Stock(
        product_id=s.product_id,
        warehouse_id=s.warehouse_id,
        physical=s.physical,
        reserved=s.reserved,
        version=s.version,
    )


def _product_to_domain(p: ProductModel) -> Product:
    return Product(
        id=p.id, store_id=p.store_id, sku=p.sku, name=p.name, wb_external_id=p.wb_external_id
    )


def _warehouse_to_domain(w: WarehouseModel) -> Warehouse:
    return Warehouse(id=w.id, name=w.name, is_active=w.is_active, archived_at=w.archived_at)


class StoreRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, store_id: UUID) -> Store | None:
        model = await self._session.get(StoreModel, store_id)
        if model is None:
            return None
        return Store(id=model.id, name=model.name)

    async def get_default(self) -> Store | None:
        model = await self._session.scalar(
            select(StoreModel).order_by(StoreModel.created_at).limit(1)
        )
        if model is None:
            return None
        return Store(id=model.id, name=model.name)

    async def create(self, store: Store) -> Store:
        model = StoreModel(id=store.id, name=store.name)
        self._session.add(model)
        await self._session.flush()
        return store


class ProductRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, product_id: UUID) -> Product | None:
        model = await self._session.get(ProductModel, product_id)
        return _product_to_domain(model) if model else None

    async def get_by_sku(self, store_id: UUID, sku: str) -> Product | None:
        model = await self._session.scalar(
            select(ProductModel).where(ProductModel.store_id == store_id, ProductModel.sku == sku)
        )
        return _product_to_domain(model) if model else None

    async def create(self, product: Product) -> Product:
        model = ProductModel(
            id=product.id,
            store_id=product.store_id,
            sku=product.sku,
            name=product.name,
            wb_external_id=product.wb_external_id,
        )
        self._session.add(model)
        await self._session.flush()
        return product

    async def update(self, product: Product) -> Product:
        await self._session.execute(
            update(ProductModel)
            .where(ProductModel.id == product.id)
            .values(sku=product.sku, name=product.name, wb_external_id=product.wb_external_id)
        )
        await self._session.flush()
        return product

    async def list(
        self, *, sku: str | None, name: str | None, offset: int, limit: int
    ) -> tuple[list[Product], int]:
        conditions = []
        if sku:
            conditions.append(ProductModel.sku.ilike(f"%{sku}%"))
        if name:
            conditions.append(ProductModel.name.ilike(f"%{name}%"))

        total = await self._session.scalar(
            select(func.count()).select_from(ProductModel).where(*conditions)
        )
        rows = await self._session.scalars(
            select(ProductModel)
            .where(*conditions)
            .order_by(ProductModel.sku)
            .offset(offset)
            .limit(limit)
        )
        return [_product_to_domain(r) for r in rows], int(total or 0)


class WarehouseRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, warehouse_id: UUID) -> Warehouse | None:
        model = await self._session.get(WarehouseModel, warehouse_id)
        return _warehouse_to_domain(model) if model else None

    async def get_by_name(self, name: str) -> Warehouse | None:
        """Возвращает АКТИВНЫЙ склад по имени.

        Имя архивированного склада свободно для переиспользования.
        """
        model = await self._session.scalar(
            select(WarehouseModel).where(
                WarehouseModel.name == name, WarehouseModel.is_active.is_(True)
            )
        )
        return _warehouse_to_domain(model) if model else None

    async def create(self, warehouse: Warehouse) -> Warehouse:
        model = WarehouseModel(id=warehouse.id, name=warehouse.name, is_active=True)
        self._session.add(model)
        await self._session.flush()
        return warehouse

    async def update(self, warehouse: Warehouse) -> Warehouse:
        await self._session.execute(
            update(WarehouseModel)
            .where(WarehouseModel.id == warehouse.id)
            .values(
                name=warehouse.name,
                is_active=warehouse.is_active,
                archived_at=warehouse.archived_at,
            )
        )
        await self._session.flush()
        return warehouse

    async def delete(self, warehouse_id: UUID) -> None:
        """Физически удаляет склад (только для полного удаления архивированного склада)."""
        await self._session.execute(delete(WarehouseModel).where(WarehouseModel.id == warehouse_id))
        await self._session.flush()

    async def references(self, warehouse_id: UUID) -> dict[str, int]:
        """Считает, сколько записей ссылаются на склад (проверка перед полным удалением)."""

        async def _count(model, *conditions):
            value = await self._session.scalar(
                select(func.count()).select_from(model).where(*conditions)
            )
            return int(value or 0)

        return {
            "stocks": await _count(StockModel, StockModel.warehouse_id == warehouse_id),
            "reservations": await _count(
                ReservationModel, ReservationModel.warehouse_id == warehouse_id
            ),
            "transfers": await _count(
                TransferModel,
                (TransferModel.source_warehouse_id == warehouse_id)
                | (TransferModel.target_warehouse_id == warehouse_id),
            ),
            "shipments": await _count(
                ShipmentModel, ShipmentModel.source_warehouse_id == warehouse_id
            ),
            "operations": await _count(
                OperationModel,
                (OperationModel.source_warehouse_id == warehouse_id)
                | (OperationModel.target_warehouse_id == warehouse_id),
            ),
            "movements": await _count(
                StockMovementModel,
                (StockMovementModel.source_warehouse_id == warehouse_id)
                | (StockMovementModel.target_warehouse_id == warehouse_id),
            ),
        }

    async def list(self, *, active_only: bool = False) -> list[Warehouse]:
        stmt = select(WarehouseModel)
        if active_only:
            stmt = stmt.where(WarehouseModel.is_active.is_(True))
        stmt = stmt.order_by(WarehouseModel.name)
        rows = await self._session.scalars(stmt)
        return [_warehouse_to_domain(r) for r in rows]


class StockRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, product_id: UUID, warehouse_id: UUID) -> Stock | None:
        model = await self._session.scalar(
            select(StockModel).where(
                StockModel.product_id == product_id,
                StockModel.warehouse_id == warehouse_id,
            )
        )
        return _stock_to_domain(model) if model else None

    async def get_for_update(self, product_id: UUID, warehouse_id: UUID) -> Stock | None:
        model = await self._session.scalar(
            select(StockModel)
            .where(
                StockModel.product_id == product_id,
                StockModel.warehouse_id == warehouse_id,
            )
            .with_for_update()
        )
        return _stock_to_domain(model) if model else None

    async def get_or_create_for_update(self, product_id: UUID, warehouse_id: UUID) -> Stock:
        await self._session.execute(
            pg_insert(StockModel)
            .values(product_id=product_id, warehouse_id=warehouse_id, physical=0, reserved=0)
            .on_conflict_do_nothing(index_elements=[StockModel.product_id, StockModel.warehouse_id])
        )
        stock = await self.get_for_update(product_id, warehouse_id)
        assert stock is not None
        return stock

    async def save(self, stock: Stock) -> None:
        await self._session.execute(
            update(StockModel)
            .where(
                StockModel.product_id == stock.product_id,
                StockModel.warehouse_id == stock.warehouse_id,
            )
            .values(
                physical=stock.physical,
                reserved=stock.reserved,
                version=StockModel.version + 1,
            )
        )
        await self._session.flush()

    async def nonzero_by_warehouse(self, warehouse_id: UUID) -> list[tuple[Stock, Product]]:
        rows = await self._session.execute(
            select(StockModel, ProductModel)
            .join(ProductModel, ProductModel.id == StockModel.product_id)
            .where(
                StockModel.warehouse_id == warehouse_id,
                StockModel.physical > 0,
            )
            .order_by(ProductModel.sku)
        )
        return [(_stock_to_domain(stock), _product_to_domain(product)) for stock, product in rows]

    async def available_by_product(
        self, product_id: UUID, exclude_warehouse_id: UUID | None
    ) -> list[tuple[Warehouse, int]]:
        stmt = (
            select(StockModel, WarehouseModel)
            .join(WarehouseModel, WarehouseModel.id == StockModel.warehouse_id)
            .where(StockModel.product_id == product_id, WarehouseModel.is_active.is_(True))
        )
        if exclude_warehouse_id is not None:
            stmt = stmt.where(StockModel.warehouse_id != exclude_warehouse_id)
        rows = await self._session.execute(stmt)
        result: list[tuple[Warehouse, int]] = []
        for stock, warehouse in rows:
            available = stock.physical - stock.reserved
            result.append((_warehouse_to_domain(warehouse), available))
        return result

    async def list_joined(
        self, *, sku: str | None, name: str | None, warehouse_id: UUID | None
    ) -> list[tuple[Stock, Product, Warehouse]]:
        stmt = (
            select(StockModel, ProductModel, WarehouseModel)
            .join(ProductModel, ProductModel.id == StockModel.product_id)
            .join(WarehouseModel, WarehouseModel.id == StockModel.warehouse_id)
        )
        conditions = []
        if sku:
            conditions.append(ProductModel.sku.ilike(f"%{sku}%"))
        if name:
            conditions.append(ProductModel.name.ilike(f"%{name}%"))
        if warehouse_id is not None:
            conditions.append(StockModel.warehouse_id == warehouse_id)
        if conditions:
            stmt = stmt.where(*conditions)
        stmt = stmt.order_by(ProductModel.sku, WarehouseModel.name)
        rows = await self._session.execute(stmt)
        return [
            (_stock_to_domain(s), _product_to_domain(p), _warehouse_to_domain(w))
            for s, p, w in rows
        ]
