"""Stock operation use cases — receipt, reservations, FBS, transfers, FBO."""

from __future__ import annotations

from domain import services as svc
from domain.entities import (
    Reservation,
    Shipment,
    ShipmentItem,
    Stock,
    Transfer,
    TransferItem,
)
from domain.enums import (
    MovementType,
    OperationType,
    ReservationStatus,
    ShipmentStatus,
    ShipmentType,
    TransferStatus,
)
from domain.events import (
    EVENT_FBO_SHIPMENT_CREATED,
    EVENT_FBO_SHIPMENT_DISPATCHED,
    EVENT_FBO_SHIPMENT_RECEIVED,
    EVENT_FBS_ORDER_SHIPPED,
    EVENT_STOCK_RECEIVED,
    EVENT_STOCK_RESERVATION_CANCELLED,
    EVENT_STOCK_RESERVED,
    EVENT_TRANSFER_CREATED,
    EVENT_TRANSFER_DISPATCHED,
    EVENT_TRANSFER_RECEIVED,
    make_event,
)
from domain.repositories.interfaces import UnitOfWork
from domain.services.state_machine import (
    FBO_SHIPMENT_TRANSITIONS,
    RESERVATION_TRANSITIONS,
    TRANSFER_TRANSITIONS,
    assert_transition,
)

from ..commands import (
    CancelReservationCommand,
    CreateFBOShipmentCommand,
    CreateTransferCommand,
    DispatchShipmentCommand,
    DispatchTransferCommand,
    ReceiveShipmentCommand,
    ReceiveStockCommand,
    ReceiveTransferCommand,
    ReserveStockCommand,
    ShipFBSCommand,
)
from ..exceptions import ConflictError, NotFoundError, ValidationError
from .base import (
    UseCase,
    get_product,
    get_warehouse,
    make_item,
    make_movement,
    make_operation,
    new_id,
    now,
    raise_shortage,
)


def _require_active(warehouse) -> None:
    if not warehouse.is_active:
        raise ConflictError(f"warehouse '{warehouse.name}' is archived and cannot be used")


def _positive(quantity: int) -> None:
    if quantity <= 0:
        raise ValidationError("quantity must be a positive integer")


async def _idempotent_op(uow: UnitOfWork, key: str | None):
    if not key:
        return None
    return await uow.operations.get_by_idempotency_key(key)


class ReceiveStockUseCase(UseCase):
    async def _run(self, uow: UnitOfWork, cmd: ReceiveStockCommand) -> Stock:
        _positive(cmd.quantity)
        warehouse = await get_warehouse(uow, cmd.warehouse_id)
        _require_active(warehouse)
        product = await get_product(uow, cmd.product_id)
        existing = await _idempotent_op(uow, cmd.idempotency_key)
        if existing is not None:
            stock = await uow.stocks.get(cmd.product_id, cmd.warehouse_id)
            if stock is not None:
                return stock

        stock = await uow.stocks.get_or_create_for_update(cmd.product_id, cmd.warehouse_id)
        stock.physical = svc.receive(stock.physical, cmd.quantity)
        await uow.stocks.save(stock)

        operation = make_operation(
            OperationType.RECEIPT,
            target_warehouse_id=cmd.warehouse_id,
            entity_type="stock",
            entity_id=None,
            idempotency_key=cmd.idempotency_key,
        )
        items = [make_item(cmd.product_id, cmd.quantity, target_warehouse_id=cmd.warehouse_id)]
        movements = [
            make_movement(
                cmd.product_id,
                cmd.quantity,
                MovementType.RECEIPT,
                target_warehouse_id=cmd.warehouse_id,
                operation_id=operation.id,
            )
        ]
        await uow.operations.create(operation, items, movements)
        await uow.outbox.add(
            make_event(
                EVENT_STOCK_RECEIVED,
                aggregate_type="stock",
                aggregate_id=stock.product_id,
                data={
                    "product_id": str(cmd.product_id),
                    "sku": product.sku,
                    "warehouse_id": str(cmd.warehouse_id),
                    "quantity": cmd.quantity,
                },
            )
        )
        return stock


class ReserveFBSStockUseCase(UseCase):
    async def _run(self, uow: UnitOfWork, cmd: ReserveStockCommand) -> Reservation:
        _positive(cmd.quantity)
        warehouse = await get_warehouse(uow, cmd.warehouse_id)
        _require_active(warehouse)
        product = await get_product(uow, cmd.product_id)
        existing = await _idempotent_op(uow, cmd.idempotency_key)
        if existing is not None and existing.entity_id:
            reservation = await uow.reservations.get(existing.entity_id)
            if reservation is not None:
                return reservation

        stock = await uow.stocks.get_for_update(cmd.product_id, cmd.warehouse_id)
        physical = stock.physical if stock else 0
        reserved = stock.reserved if stock else 0
        if not svc.can_reserve(physical, reserved, cmd.quantity):
            await raise_shortage(uow, product, cmd.warehouse_id, cmd.quantity, physical - reserved)

        if stock is None:
            stock = await uow.stocks.get_or_create_for_update(cmd.product_id, cmd.warehouse_id)
        stock.reserved = reserved + cmd.quantity
        await uow.stocks.save(stock)

        operation = make_operation(
            OperationType.RESERVE,
            target_warehouse_id=cmd.warehouse_id,
            idempotency_key=cmd.idempotency_key,
        )
        reservation = Reservation(
            id=new_id(),
            product_id=cmd.product_id,
            warehouse_id=cmd.warehouse_id,
            quantity=cmd.quantity,
            status=ReservationStatus.ACTIVE,
            operation_id=operation.id,
            created_at=now(),
        )
        operation.entity_type = "reservation"
        operation.entity_id = reservation.id
        await uow.reservations.create(reservation)
        items = [make_item(cmd.product_id, cmd.quantity, target_warehouse_id=cmd.warehouse_id)]
        await uow.operations.create(operation, items, [])
        await uow.outbox.add(
            make_event(
                EVENT_STOCK_RESERVED,
                aggregate_type="reservation",
                aggregate_id=reservation.id,
                data={
                    "reservation_id": str(reservation.id),
                    "product_id": str(cmd.product_id),
                    "sku": product.sku,
                    "warehouse_id": str(cmd.warehouse_id),
                    "quantity": cmd.quantity,
                },
            )
        )
        return reservation


class CancelFBSReservationUseCase(UseCase):
    async def _run(self, uow: UnitOfWork, cmd: CancelReservationCommand) -> Reservation:
        reservation = await uow.reservations.get_for_update(cmd.reservation_id)
        if reservation is None:
            raise NotFoundError(f"reservation {cmd.reservation_id} not found")
        if reservation.status is ReservationStatus.CANCELLED:
            return reservation
        assert_transition(reservation.status, ReservationStatus.CANCELLED, RESERVATION_TRANSITIONS)

        stock = await uow.stocks.get_for_update(reservation.product_id, reservation.warehouse_id)
        if stock is None:
            raise ConflictError("reservation has no corresponding stock row")
        new_physical, new_reserved = svc.release(
            stock.physical, stock.reserved, reservation.quantity
        )
        stock.physical, stock.reserved = new_physical, new_reserved
        await uow.stocks.save(stock)

        reservation.status = ReservationStatus.CANCELLED
        reservation.cancelled_at = now()
        await uow.reservations.save(reservation)

        product = await get_product(uow, reservation.product_id)
        operation = make_operation(
            OperationType.RESERVE_CANCEL,
            source_warehouse_id=reservation.warehouse_id,
            entity_type="reservation",
            entity_id=reservation.id,
        )
        items = [
            make_item(
                reservation.product_id,
                reservation.quantity,
                source_warehouse_id=reservation.warehouse_id,
            )
        ]
        await uow.operations.create(operation, items, [])
        await uow.outbox.add(
            make_event(
                EVENT_STOCK_RESERVATION_CANCELLED,
                aggregate_type="reservation",
                aggregate_id=reservation.id,
                data={
                    "reservation_id": str(reservation.id),
                    "product_id": str(reservation.product_id),
                    "sku": product.sku,
                    "warehouse_id": str(reservation.warehouse_id),
                    "quantity": reservation.quantity,
                },
            )
        )
        return reservation


class ShipFBSOrderUseCase(UseCase):
    async def _run(self, uow: UnitOfWork, cmd: ShipFBSCommand) -> Shipment:
        existing = await _idempotent_op(uow, cmd.idempotency_key)
        if existing is not None and existing.entity_id:
            shipment = await uow.shipments.get(existing.entity_id)
            if shipment is not None:
                return shipment

        reservation = await uow.reservations.get_for_update(cmd.reservation_id)
        if reservation is None:
            raise NotFoundError(f"reservation {cmd.reservation_id} not found")
        if reservation.status is ReservationStatus.SHIPPED:
            shipment = await uow.shipments.get_by_reservation(reservation.id)
            if shipment is not None:
                return shipment
            raise ConflictError("reservation already shipped but shipment not found")
        assert_transition(reservation.status, ReservationStatus.SHIPPED, RESERVATION_TRANSITIONS)

        stock = await uow.stocks.get_for_update(reservation.product_id, reservation.warehouse_id)
        if stock is None or stock.reserved < reservation.quantity:
            raise ConflictError("reservation quantity exceeds reserved stock")
        stock.physical, stock.reserved = svc.deduct(
            stock.physical, stock.reserved, reservation.quantity
        )
        await uow.stocks.save(stock)

        reservation.status = ReservationStatus.SHIPPED
        reservation.shipped_at = now()
        await uow.reservations.save(reservation)

        product = await get_product(uow, reservation.product_id)
        shipment = Shipment(
            id=new_id(),
            type=ShipmentType.FBS,
            source_warehouse_id=reservation.warehouse_id,
            status=ShipmentStatus.SHIPPED,
            destination="customer",
            reservation_id=reservation.id,
            items=[ShipmentItem(product_id=reservation.product_id, quantity=reservation.quantity)],
            created_at=now(),
            dispatched_at=now(),
        )
        await uow.shipments.create(shipment)

        operation = make_operation(
            OperationType.FBS_SHIP,
            source_warehouse_id=reservation.warehouse_id,
            entity_type="shipment",
            entity_id=shipment.id,
            idempotency_key=cmd.idempotency_key,
        )
        items = [
            make_item(
                reservation.product_id,
                reservation.quantity,
                source_warehouse_id=reservation.warehouse_id,
            )
        ]
        movements = [
            make_movement(
                reservation.product_id,
                reservation.quantity,
                MovementType.FBS_SHIP,
                source_warehouse_id=reservation.warehouse_id,
                operation_id=operation.id,
            )
        ]
        await uow.operations.create(operation, items, movements)
        await uow.outbox.add(
            make_event(
                EVENT_FBS_ORDER_SHIPPED,
                aggregate_type="shipment",
                aggregate_id=shipment.id,
                data={
                    "shipment_id": str(shipment.id),
                    "reservation_id": str(reservation.id),
                    "product_id": str(reservation.product_id),
                    "sku": product.sku,
                    "warehouse_id": str(reservation.warehouse_id),
                    "quantity": reservation.quantity,
                },
            )
        )
        return shipment


class CreateTransferUseCase(UseCase):
    async def _run(self, uow: UnitOfWork, cmd: CreateTransferCommand) -> Transfer:
        if not cmd.items:
            raise ValidationError("transfer must contain at least one item")
        if cmd.source_warehouse_id == cmd.target_warehouse_id:
            raise ValidationError("source and target warehouses must differ")
        source = await get_warehouse(uow, cmd.source_warehouse_id)
        target = await get_warehouse(uow, cmd.target_warehouse_id)
        _require_active(source)
        _require_active(target)

        existing = await _idempotent_op(uow, cmd.idempotency_key)
        if existing is not None and existing.entity_id:
            transfer = await uow.transfers.get(existing.entity_id)
            if transfer is not None:
                return transfer

        items = []
        for line in cmd.items:
            _positive(line.quantity)
            await get_product(uow, line.product_id)
            stock = await uow.stocks.get(line.product_id, cmd.source_warehouse_id)
            physical = stock.physical if stock else 0
            reserved = stock.reserved if stock else 0
            if not svc.can_deduct(physical, reserved, line.quantity):
                product = await get_product(uow, line.product_id)
                await raise_shortage(
                    uow, product, cmd.source_warehouse_id, line.quantity, physical - reserved
                )
            items.append(TransferItem(product_id=line.product_id, quantity=line.quantity))

        transfer = Transfer(
            id=new_id(),
            source_warehouse_id=cmd.source_warehouse_id,
            target_warehouse_id=cmd.target_warehouse_id,
            status=TransferStatus.DRAFT,
            items=items,
            created_at=now(),
        )
        await uow.transfers.create(transfer)

        operation = make_operation(
            OperationType.TRANSFER_CREATE,
            source_warehouse_id=cmd.source_warehouse_id,
            target_warehouse_id=cmd.target_warehouse_id,
            entity_type="transfer",
            entity_id=transfer.id,
            idempotency_key=cmd.idempotency_key,
        )
        op_items = [
            make_item(
                line.product_id,
                line.quantity,
                source_warehouse_id=cmd.source_warehouse_id,
                target_warehouse_id=cmd.target_warehouse_id,
            )
            for line in cmd.items
        ]
        await uow.operations.create(operation, op_items, [])
        await uow.outbox.add(
            make_event(
                EVENT_TRANSFER_CREATED,
                aggregate_type="transfer",
                aggregate_id=transfer.id,
                data={
                    "transfer_id": str(transfer.id),
                    "source_warehouse_id": str(cmd.source_warehouse_id),
                    "target_warehouse_id": str(cmd.target_warehouse_id),
                },
            )
        )
        return transfer


class DispatchTransferUseCase(UseCase):
    async def _run(self, uow: UnitOfWork, cmd: DispatchTransferCommand) -> Transfer:
        transfer = await uow.transfers.get_for_update(cmd.transfer_id)
        if transfer is None:
            raise NotFoundError(f"transfer {cmd.transfer_id} not found")
        if (
            transfer.status is TransferStatus.IN_TRANSIT
            or transfer.status is TransferStatus.RECEIVED
        ):
            return transfer
        assert_transition(transfer.status, TransferStatus.IN_TRANSIT, TRANSFER_TRANSITIONS)

        for item in transfer.items:
            product = await get_product(uow, item.product_id)
            stock = await uow.stocks.get_for_update(item.product_id, transfer.source_warehouse_id)
            physical = stock.physical if stock else 0
            reserved = stock.reserved if stock else 0
            if not svc.can_deduct(physical, reserved, item.quantity):
                await raise_shortage(
                    uow, product, transfer.source_warehouse_id, item.quantity, physical - reserved
                )
            if stock is None:
                raise ConflictError("source stock row missing")
            stock.physical, stock.reserved = svc.deduct_available(
                stock.physical, stock.reserved, item.quantity
            )
            await uow.stocks.save(stock)

        transfer.status = TransferStatus.IN_TRANSIT
        transfer.dispatched_at = now()
        await uow.transfers.save(transfer)

        operation = make_operation(
            OperationType.TRANSFER_DISPATCH,
            source_warehouse_id=transfer.source_warehouse_id,
            target_warehouse_id=transfer.target_warehouse_id,
            entity_type="transfer",
            entity_id=transfer.id,
        )
        op_items = [
            make_item(
                item.product_id,
                item.quantity,
                source_warehouse_id=transfer.source_warehouse_id,
                target_warehouse_id=transfer.target_warehouse_id,
            )
            for item in transfer.items
        ]
        movements = [
            make_movement(
                item.product_id,
                item.quantity,
                MovementType.TRANSFER_DISPATCH,
                source_warehouse_id=transfer.source_warehouse_id,
                target_warehouse_id=transfer.target_warehouse_id,
                operation_id=operation.id,
            )
            for item in transfer.items
        ]
        await uow.operations.create(operation, op_items, movements)
        await uow.outbox.add(
            make_event(
                EVENT_TRANSFER_DISPATCHED,
                aggregate_type="transfer",
                aggregate_id=transfer.id,
                data={
                    "transfer_id": str(transfer.id),
                    "source_warehouse_id": str(transfer.source_warehouse_id),
                    "target_warehouse_id": str(transfer.target_warehouse_id),
                },
            )
        )
        return transfer


class ReceiveTransferUseCase(UseCase):
    async def _run(self, uow: UnitOfWork, cmd: ReceiveTransferCommand) -> Transfer:
        transfer = await uow.transfers.get_for_update(cmd.transfer_id)
        if transfer is None:
            raise NotFoundError(f"transfer {cmd.transfer_id} not found")
        if transfer.status is TransferStatus.RECEIVED:
            return transfer
        assert_transition(transfer.status, TransferStatus.RECEIVED, TRANSFER_TRANSITIONS)

        for item in transfer.items:
            stock = await uow.stocks.get_or_create_for_update(
                item.product_id, transfer.target_warehouse_id
            )
            stock.physical = svc.receive(stock.physical, item.quantity)
            await uow.stocks.save(stock)

        transfer.status = TransferStatus.RECEIVED
        transfer.received_at = now()
        await uow.transfers.save(transfer)

        operation = make_operation(
            OperationType.TRANSFER_RECEIVE,
            source_warehouse_id=transfer.source_warehouse_id,
            target_warehouse_id=transfer.target_warehouse_id,
            entity_type="transfer",
            entity_id=transfer.id,
        )
        op_items = [
            make_item(
                item.product_id,
                item.quantity,
                source_warehouse_id=transfer.source_warehouse_id,
                target_warehouse_id=transfer.target_warehouse_id,
            )
            for item in transfer.items
        ]
        movements = [
            make_movement(
                item.product_id,
                item.quantity,
                MovementType.TRANSFER_RECEIVE,
                source_warehouse_id=transfer.source_warehouse_id,
                target_warehouse_id=transfer.target_warehouse_id,
                operation_id=operation.id,
            )
            for item in transfer.items
        ]
        await uow.operations.create(operation, op_items, movements)
        await uow.outbox.add(
            make_event(
                EVENT_TRANSFER_RECEIVED,
                aggregate_type="transfer",
                aggregate_id=transfer.id,
                data={
                    "transfer_id": str(transfer.id),
                    "source_warehouse_id": str(transfer.source_warehouse_id),
                    "target_warehouse_id": str(transfer.target_warehouse_id),
                },
            )
        )
        return transfer


class CreateFBOShipmentUseCase(UseCase):
    async def _run(self, uow: UnitOfWork, cmd: CreateFBOShipmentCommand) -> Shipment:
        if not cmd.items:
            raise ValidationError("shipment must contain at least one item")
        source = await get_warehouse(uow, cmd.source_warehouse_id)
        _require_active(source)
        existing = await _idempotent_op(uow, cmd.idempotency_key)
        if existing is not None and existing.entity_id:
            shipment = await uow.shipments.get(existing.entity_id)
            if shipment is not None:
                return shipment

        items = []
        for line in cmd.items:
            _positive(line.quantity)
            await get_product(uow, line.product_id)
            stock = await uow.stocks.get(line.product_id, cmd.source_warehouse_id)
            physical = stock.physical if stock else 0
            reserved = stock.reserved if stock else 0
            if not svc.can_deduct(physical, reserved, line.quantity):
                product = await get_product(uow, line.product_id)
                await raise_shortage(
                    uow, product, cmd.source_warehouse_id, line.quantity, physical - reserved
                )
            items.append(ShipmentItem(product_id=line.product_id, quantity=line.quantity))

        shipment = Shipment(
            id=new_id(),
            type=ShipmentType.FBO,
            source_warehouse_id=cmd.source_warehouse_id,
            status=ShipmentStatus.DRAFT,
            destination="Wildberries",
            items=items,
            created_at=now(),
        )
        await uow.shipments.create(shipment)

        operation = make_operation(
            OperationType.FBO_CREATE,
            source_warehouse_id=cmd.source_warehouse_id,
            entity_type="shipment",
            entity_id=shipment.id,
            idempotency_key=cmd.idempotency_key,
        )
        op_items = [
            make_item(line.product_id, line.quantity, source_warehouse_id=cmd.source_warehouse_id)
            for line in cmd.items
        ]
        await uow.operations.create(operation, op_items, [])
        await uow.outbox.add(
            make_event(
                EVENT_FBO_SHIPMENT_CREATED,
                aggregate_type="shipment",
                aggregate_id=shipment.id,
                data={
                    "shipment_id": str(shipment.id),
                    "source_warehouse_id": str(cmd.source_warehouse_id),
                },
            )
        )
        return shipment


class DispatchFBOShipmentUseCase(UseCase):
    async def _run(self, uow: UnitOfWork, cmd: DispatchShipmentCommand) -> Shipment:
        shipment = await uow.shipments.get_for_update(cmd.shipment_id)
        if shipment is None:
            raise NotFoundError(f"shipment {cmd.shipment_id} not found")
        if shipment.type is not ShipmentType.FBO:
            raise ConflictError("only FBO shipments use dispatch/receive flow")
        if shipment.status in (ShipmentStatus.IN_TRANSIT, ShipmentStatus.RECEIVED):
            return shipment
        assert_transition(shipment.status, ShipmentStatus.IN_TRANSIT, FBO_SHIPMENT_TRANSITIONS)

        for item in shipment.items:
            product = await get_product(uow, item.product_id)
            stock = await uow.stocks.get_for_update(item.product_id, shipment.source_warehouse_id)
            physical = stock.physical if stock else 0
            if not svc.can_deduct(physical, 0, item.quantity):
                await raise_shortage(
                    uow, product, shipment.source_warehouse_id, item.quantity, physical
                )
            if stock is None:
                raise ConflictError("source stock row missing")
            stock.physical = svc.deduct_physical(stock.physical, item.quantity)
            await uow.stocks.save(stock)

        shipment.status = ShipmentStatus.IN_TRANSIT
        shipment.dispatched_at = now()
        await uow.shipments.save(shipment)

        operation = make_operation(
            OperationType.FBO_DISPATCH,
            source_warehouse_id=shipment.source_warehouse_id,
            entity_type="shipment",
            entity_id=shipment.id,
        )
        op_items = [
            make_item(
                item.product_id, item.quantity, source_warehouse_id=shipment.source_warehouse_id
            )
            for item in shipment.items
        ]
        movements = [
            make_movement(
                item.product_id,
                item.quantity,
                MovementType.FBO_DISPATCH,
                source_warehouse_id=shipment.source_warehouse_id,
                operation_id=operation.id,
            )
            for item in shipment.items
        ]
        await uow.operations.create(operation, op_items, movements)
        await uow.outbox.add(
            make_event(
                EVENT_FBO_SHIPMENT_DISPATCHED,
                aggregate_type="shipment",
                aggregate_id=shipment.id,
                data={"shipment_id": str(shipment.id)},
            )
        )
        return shipment


class ReceiveFBOShipmentUseCase(UseCase):
    async def _run(self, uow: UnitOfWork, cmd: ReceiveShipmentCommand) -> Shipment:
        shipment = await uow.shipments.get_for_update(cmd.shipment_id)
        if shipment is None:
            raise NotFoundError(f"shipment {cmd.shipment_id} not found")
        if shipment.type is not ShipmentType.FBO:
            raise ConflictError("only FBO shipments use dispatch/receive flow")
        if shipment.status is ShipmentStatus.RECEIVED:
            return shipment
        assert_transition(shipment.status, ShipmentStatus.RECEIVED, FBO_SHIPMENT_TRANSITIONS)

        shipment.status = ShipmentStatus.RECEIVED
        shipment.received_at = now()
        await uow.shipments.save(shipment)

        operation = make_operation(
            OperationType.FBO_RECEIVE,
            source_warehouse_id=shipment.source_warehouse_id,
            entity_type="shipment",
            entity_id=shipment.id,
        )
        op_items = [
            make_item(
                item.product_id, item.quantity, source_warehouse_id=shipment.source_warehouse_id
            )
            for item in shipment.items
        ]
        await uow.operations.create(operation, op_items, [])
        await uow.outbox.add(
            make_event(
                EVENT_FBO_SHIPMENT_RECEIVED,
                aggregate_type="shipment",
                aggregate_id=shipment.id,
                data={"shipment_id": str(shipment.id)},
            )
        )
        return shipment
