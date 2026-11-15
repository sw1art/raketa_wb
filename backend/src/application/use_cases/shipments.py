"""Listing use cases: shipments, reservations, transfers."""

from __future__ import annotations

from domain.entities import ReservationView, Shipment, TransferView
from domain.enums import ShipmentStatus, ShipmentType
from domain.repositories.interfaces import UnitOfWork

from ..commands import ListQuery
from .base import UseCase


class ListShipmentsUseCase(UseCase):
    async def _run(
        self,
        uow: UnitOfWork,
        *,
        shipment_type: ShipmentType | None = None,
        status: ShipmentStatus | None = None,
        query: ListQuery,
    ) -> tuple[list[Shipment], int]:
        return await uow.shipments.list(
            shipment_type=shipment_type,
            status=status,
            offset=query.offset,
            limit=query.limit,
        )


class ListReservationsUseCase(UseCase):
    async def _run(self, uow: UnitOfWork, *, status: str | None = None) -> list[ReservationView]:
        return await uow.reservations.list_joined(status=status)


class ListTransfersUseCase(UseCase):
    async def _run(self, uow: UnitOfWork, *, status: str | None = None) -> list[TransferView]:
        return await uow.transfers.list_joined(status=status)
