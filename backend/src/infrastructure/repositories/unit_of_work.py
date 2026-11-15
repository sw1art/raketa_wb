"""SQLAlchemy UnitOfWork implementing the domain UnitOfWork port."""
from __future__ import annotations

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from application.exceptions import IdempotencyConflictError
from domain.repositories.interfaces import UnitOfWork as UnitOfWorkPort
from infrastructure.repositories.catalog import (
    ProductRepository,
    StockRepository,
    StoreRepository,
    WarehouseRepository,
)
from infrastructure.repositories.operations import OperationRepository, OutboxRepository
from infrastructure.repositories.warehouse_ops import (
    ReservationRepository,
    ShipmentRepository,
    TransferRepository,
)


class UnitOfWork(UnitOfWorkPort):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self.stores = StoreRepository(session)
        self.products = ProductRepository(session)
        self.warehouses = WarehouseRepository(session)
        self.stocks = StockRepository(session)
        self.reservations = ReservationRepository(session)
        self.transfers = TransferRepository(session)
        self.shipments = ShipmentRepository(session)
        self.operations = OperationRepository(session)
        self.outbox = OutboxRepository(session)

    async def commit(self) -> None:
        try:
            await self._session.commit()
        except IntegrityError as exc:
            await self._session.rollback()
            if "idempotency_key" in str(exc.orig):
                raise IdempotencyConflictError(
                    "this idempotency key was already used for another operation"
                ) from exc
            raise

    async def rollback(self) -> None:
        await self._session.rollback()

    async def close(self) -> None:
        await self._session.close()
