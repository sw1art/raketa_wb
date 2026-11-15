"""Reservation, Transfer and Shipment repositories."""
from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from domain.entities import (
    Reservation,
    ReservationView,
    Shipment,
    ShipmentItem,
    Transfer,
    TransferItem,
    TransferItemView,
    TransferView,
)
from domain.enums import ReservationStatus, ShipmentStatus, ShipmentType, TransferStatus
from infrastructure.database.models import Product as ProductModel
from infrastructure.database.models import Reservation as ReservationModel
from infrastructure.database.models import Shipment as ShipmentModel
from infrastructure.database.models import ShipmentItem as ShipmentItemModel
from infrastructure.database.models import Transfer as TransferModel
from infrastructure.database.models import TransferItem as TransferItemModel
from infrastructure.database.models import Warehouse as WarehouseModel

_OPEN_TRANSFER_STATUSES = (TransferStatus.DRAFT, TransferStatus.IN_TRANSIT)
_OPEN_SHIPMENT_STATUSES = (ShipmentStatus.DRAFT, ShipmentStatus.IN_TRANSIT)


def _reservation_to_domain(r: ReservationModel) -> Reservation:
    return Reservation(
        id=r.id,
        product_id=r.product_id,
        warehouse_id=r.warehouse_id,
        quantity=r.quantity,
        status=r.status,
        operation_id=r.operation_id,
        created_at=r.created_at,
        cancelled_at=r.cancelled_at,
        shipped_at=r.shipped_at,
    )


class ReservationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, reservation_id: UUID) -> Reservation | None:
        model = await self._session.get(ReservationModel, reservation_id)
        return _reservation_to_domain(model) if model else None

    async def get_for_update(self, reservation_id: UUID) -> Reservation | None:
        model = await self._session.scalar(
            select(ReservationModel)
            .where(ReservationModel.id == reservation_id)
            .with_for_update()
        )
        return _reservation_to_domain(model) if model else None

    async def create(self, reservation: Reservation) -> Reservation:
        model = ReservationModel(
            id=reservation.id,
            product_id=reservation.product_id,
            warehouse_id=reservation.warehouse_id,
            quantity=reservation.quantity,
            status=reservation.status,
            operation_id=reservation.operation_id,
            created_at=reservation.created_at,
        )
        self._session.add(model)
        await self._session.flush()
        return reservation

    async def save(self, reservation: Reservation) -> Reservation:
        await self._session.execute(
            update(ReservationModel)
            .where(ReservationModel.id == reservation.id)
            .values(
                status=reservation.status,
                cancelled_at=reservation.cancelled_at,
                shipped_at=reservation.shipped_at,
            )
        )
        await self._session.flush()
        return reservation

    async def count_active_by_warehouse(self, warehouse_id: UUID) -> int:
        count = await self._session.scalar(
            select(func.count())
            .select_from(ReservationModel)
            .where(
                ReservationModel.warehouse_id == warehouse_id,
                ReservationModel.status == ReservationStatus.ACTIVE,
            )
        )
        return int(count or 0)

    async def list_joined(self, *, status: str | None) -> list[ReservationView]:
        stmt = (
            select(ReservationModel, ProductModel, WarehouseModel)
            .join(ProductModel, ProductModel.id == ReservationModel.product_id)
            .join(WarehouseModel, WarehouseModel.id == ReservationModel.warehouse_id)
        )
        if status is not None:
            stmt = stmt.where(ReservationModel.status == status)
        stmt = stmt.order_by(ReservationModel.created_at.desc())
        rows = await self._session.execute(stmt)
        return [
            ReservationView(
                id=r.id,
                product_id=r.product_id,
                warehouse_id=r.warehouse_id,
                sku=p.sku,
                product_name=p.name,
                warehouse_name=w.name,
                quantity=r.quantity,
                status=r.status.value if hasattr(r.status, "value") else str(r.status),
                created_at=r.created_at,
            )
            for r, p, w in rows
        ]


class TransferRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def _load(self, transfer_id: UUID, *, for_update: bool) -> Transfer | None:
        stmt = select(TransferModel).where(TransferModel.id == transfer_id)
        if for_update:
            stmt = stmt.with_for_update()
        model = await self._session.scalar(stmt)
        if model is None:
            return None
        items = await self._session.scalars(
            select(TransferItemModel).where(TransferItemModel.transfer_id == transfer_id)
        )
        return Transfer(
            id=model.id,
            source_warehouse_id=model.source_warehouse_id,
            target_warehouse_id=model.target_warehouse_id,
            status=model.status,
            items=[TransferItem(product_id=i.product_id, quantity=i.quantity) for i in items],
            created_at=model.created_at,
            dispatched_at=model.dispatched_at,
            received_at=model.received_at,
        )

    async def get(self, transfer_id: UUID) -> Transfer | None:
        return await self._load(transfer_id, for_update=False)

    async def get_for_update(self, transfer_id: UUID) -> Transfer | None:
        return await self._load(transfer_id, for_update=True)

    async def create(self, transfer: Transfer) -> Transfer:
        model = TransferModel(
            id=transfer.id,
            source_warehouse_id=transfer.source_warehouse_id,
            target_warehouse_id=transfer.target_warehouse_id,
            status=transfer.status,
            created_at=transfer.created_at,
        )
        self._session.add(model)
        for item in transfer.items:
            self._session.add(
                TransferItemModel(
                    transfer_id=transfer.id,
                    product_id=item.product_id,
                    quantity=item.quantity,
                )
            )
        await self._session.flush()
        return transfer

    async def save(self, transfer: Transfer) -> Transfer:
        await self._session.execute(
            update(TransferModel)
            .where(TransferModel.id == transfer.id)
            .values(
                status=transfer.status,
                dispatched_at=transfer.dispatched_at,
                received_at=transfer.received_at,
            )
        )
        await self._session.flush()
        return transfer

    async def count_open_by_warehouse(self, warehouse_id: UUID) -> int:
        count = await self._session.scalar(
            select(func.count())
            .select_from(TransferModel)
            .where(
                TransferModel.status.in_(_OPEN_TRANSFER_STATUSES),
                (
                    (TransferModel.source_warehouse_id == warehouse_id)
                    | (TransferModel.target_warehouse_id == warehouse_id)
                ),
            )
        )
        return int(count or 0)

    async def list_in_transit(self) -> list[Transfer]:
        transfers = await self._session.scalars(
            select(TransferModel).where(TransferModel.status == TransferStatus.IN_TRANSIT)
        )
        transfer_list = list(transfers)
        if not transfer_list:
            return []
        ids = [t.id for t in transfer_list]
        items = await self._session.scalars(
            select(TransferItemModel).where(TransferItemModel.transfer_id.in_(ids))
        )
        items_by_transfer: dict[UUID, list[TransferItem]] = {}
        for item in items:
            items_by_transfer.setdefault(item.transfer_id, []).append(
                TransferItem(product_id=item.product_id, quantity=item.quantity)
            )
        result = []
        for model in transfer_list:
            result.append(
                Transfer(
                    id=model.id,
                    source_warehouse_id=model.source_warehouse_id,
                    target_warehouse_id=model.target_warehouse_id,
                    status=model.status,
                    items=items_by_transfer.get(model.id, []),
                    created_at=model.created_at,
                    dispatched_at=model.dispatched_at,
                    received_at=model.received_at,
                )
            )
        return result

    async def list_joined(self, *, status: str | None) -> list[TransferView]:
        src = aliased(WarehouseModel)
        dst = aliased(WarehouseModel)
        stmt = (
            select(TransferModel, src, dst)
            .join(src, src.id == TransferModel.source_warehouse_id)
            .join(dst, dst.id == TransferModel.target_warehouse_id)
        )
        if status is not None:
            stmt = stmt.where(TransferModel.status == status)
        stmt = stmt.order_by(TransferModel.created_at.desc())
        rows = await self._session.execute(stmt)
        transfers = [(t, s, d) for t, s, d in rows]
        if not transfers:
            return []
        ids = [t.id for t, _, _ in transfers]
        items = await self._session.execute(
            select(TransferItemModel, ProductModel)
            .join(ProductModel, ProductModel.id == TransferItemModel.product_id)
            .where(TransferItemModel.transfer_id.in_(ids))
        )
        items_by: dict[UUID, list[TransferItemView]] = {}
        for item, product in items:
            items_by.setdefault(item.transfer_id, []).append(
                TransferItemView(
                    product_id=item.product_id, sku=product.sku, quantity=item.quantity
                )
            )
        return [
            TransferView(
                id=t.id,
                source_warehouse_id=t.source_warehouse_id,
                source_warehouse_name=s.name,
                target_warehouse_id=t.target_warehouse_id,
                target_warehouse_name=d.name,
                status=t.status.value if hasattr(t.status, "value") else str(t.status),
                items=items_by.get(t.id, []),
                created_at=t.created_at,
                dispatched_at=t.dispatched_at,
                received_at=t.received_at,
            )
            for t, s, d in transfers
        ]


def _shipment_to_domain(s: ShipmentModel, items: list[ShipmentItemModel]) -> Shipment:
    return Shipment(
        id=s.id,
        type=s.type,
        source_warehouse_id=s.source_warehouse_id,
        status=s.status,
        destination=s.destination,
        external_status=s.external_status,
        reservation_id=s.reservation_id,
        items=[ShipmentItem(product_id=i.product_id, quantity=i.quantity) for i in items],
        created_at=s.created_at,
        dispatched_at=s.dispatched_at,
        received_at=s.received_at,
    )


class ShipmentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def _load(self, shipment_id: UUID, *, for_update: bool) -> Shipment | None:
        stmt = select(ShipmentModel).where(ShipmentModel.id == shipment_id)
        if for_update:
            stmt = stmt.with_for_update()
        model = await self._session.scalar(stmt)
        if model is None:
            return None
        items = await self._session.scalars(
            select(ShipmentItemModel).where(ShipmentItemModel.shipment_id == shipment_id)
        )
        return _shipment_to_domain(model, list(items))

    async def get(self, shipment_id: UUID) -> Shipment | None:
        return await self._load(shipment_id, for_update=False)

    async def get_for_update(self, shipment_id: UUID) -> Shipment | None:
        return await self._load(shipment_id, for_update=True)

    async def get_by_reservation(self, reservation_id: UUID) -> Shipment | None:
        model = await self._session.scalar(
            select(ShipmentModel).where(ShipmentModel.reservation_id == reservation_id)
        )
        if model is None:
            return None
        items = await self._session.scalars(
            select(ShipmentItemModel).where(ShipmentItemModel.shipment_id == model.id)
        )
        return _shipment_to_domain(model, list(items))

    async def create(self, shipment: Shipment) -> Shipment:
        model = ShipmentModel(
            id=shipment.id,
            type=shipment.type,
            source_warehouse_id=shipment.source_warehouse_id,
            status=shipment.status,
            destination=shipment.destination,
            external_status=shipment.external_status,
            reservation_id=shipment.reservation_id,
            created_at=shipment.created_at,
            dispatched_at=shipment.dispatched_at,
            received_at=shipment.received_at,
        )
        self._session.add(model)
        for item in shipment.items:
            self._session.add(
                ShipmentItemModel(
                    shipment_id=shipment.id,
                    product_id=item.product_id,
                    quantity=item.quantity,
                )
            )
        await self._session.flush()
        return shipment

    async def save(self, shipment: Shipment) -> Shipment:
        await self._session.execute(
            update(ShipmentModel)
            .where(ShipmentModel.id == shipment.id)
            .values(
                status=shipment.status,
                external_status=shipment.external_status,
                dispatched_at=shipment.dispatched_at,
                received_at=shipment.received_at,
            )
        )
        await self._session.flush()
        return shipment

    async def count_open_by_warehouse(self, warehouse_id: UUID) -> int:
        count = await self._session.scalar(
            select(func.count())
            .select_from(ShipmentModel)
            .where(
                ShipmentModel.source_warehouse_id == warehouse_id,
                ShipmentModel.status.in_(_OPEN_SHIPMENT_STATUSES),
            )
        )
        return int(count or 0)

    async def list_in_transit(self) -> list[Shipment]:
        shipments = await self._session.scalars(
            select(ShipmentModel).where(
                (
                    (ShipmentModel.type == ShipmentType.FBO)
                    & (ShipmentModel.status == ShipmentStatus.IN_TRANSIT)
                )
                | (
                    (ShipmentModel.type == ShipmentType.FBS)
                    & (ShipmentModel.status == ShipmentStatus.SHIPPED)
                )
            )
        )
        shipment_list = list(shipments)
        if not shipment_list:
            return []
        ids = [s.id for s in shipment_list]
        items = await self._session.scalars(
            select(ShipmentItemModel).where(ShipmentItemModel.shipment_id.in_(ids))
        )
        items_by_shipment: dict[UUID, list[ShipmentItemModel]] = {}
        for item in items:
            items_by_shipment.setdefault(item.shipment_id, []).append(item)
        return [
            _shipment_to_domain(s, items_by_shipment.get(s.id, [])) for s in shipment_list
        ]

    async def list(
        self,
        *,
        shipment_type: ShipmentType | None,
        status: ShipmentStatus | None,
        offset: int,
        limit: int,
    ) -> tuple[list[Shipment], int]:
        conditions = []
        if shipment_type is not None:
            conditions.append(ShipmentModel.type == shipment_type)
        if status is not None:
            conditions.append(ShipmentModel.status == status)
        total = await self._session.scalar(
            select(func.count()).select_from(ShipmentModel).where(*conditions)
        )
        rows = await self._session.scalars(
            select(ShipmentModel)
            .where(*conditions)
            .order_by(ShipmentModel.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        shipment_list = list(rows)
        if not shipment_list:
            return [], int(total or 0)
        ids = [s.id for s in shipment_list]
        items = await self._session.scalars(
            select(ShipmentItemModel).where(ShipmentItemModel.shipment_id.in_(ids))
        )
        items_by_shipment: dict[UUID, list[ShipmentItemModel]] = {}
        for item in items:
            items_by_shipment.setdefault(item.shipment_id, []).append(item)
        return (
            [_shipment_to_domain(s, items_by_shipment.get(s.id, [])) for s in shipment_list],
            int(total or 0),
        )
