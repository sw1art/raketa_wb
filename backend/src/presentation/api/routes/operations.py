"""Эндпоинты складских операций: приход, резервы, перемещения, отправки.

Каждая команда меняет складской баланс в одной транзакции PostgreSQL. Критические
команды принимают опциональный заголовок `Idempotency-Key` для идемпотентности.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, Header

from application.commands import (
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
from application.use_cases import (
    CancelFBSReservationUseCase,
    CreateFBOShipmentUseCase,
    CreateTransferUseCase,
    DispatchFBOShipmentUseCase,
    DispatchTransferUseCase,
    ReceiveFBOShipmentUseCase,
    ReceiveStockUseCase,
    ReceiveTransferUseCase,
    ReserveFBSStockUseCase,
    ShipFBSOrderUseCase,
)
from domain.repositories.interfaces import UnitOfWork
from presentation.api.dependencies import get_uow
from presentation.api.schemas import (
    CreateFBORequest,
    CreateTransferRequest,
    ReceiveStockRequest,
    ReservationOut,
    ReserveStockRequest,
    ShipFBSRequest,
    ShipmentOut,
    StockOut,
    TransferOut,
)

router = APIRouter(prefix="/operations", tags=["operations"])


def _idempotency(value: str | None) -> str | None:
    """Нормализует пустой заголовок Idempotency-Key в None."""
    return value if value else None


@router.post(
    "/receipts",
    response_model=StockOut,
    status_code=201,
    summary="Приход товара",
    response_description="Обновлённый остаток SKU на складе (physical увеличился).",
)
async def receive_stock(
    body: ReceiveStockRequest,
    uow: UnitOfWork = Depends(get_uow),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> StockOut:
    """Оформляет приход товара на выбранный склад.

    Событие домена: `StockReceived`.
    """
    stock = await ReceiveStockUseCase().execute(
        uow,
        ReceiveStockCommand(
            warehouse_id=body.warehouse_id,
            product_id=body.product_id,
            quantity=body.quantity,
            idempotency_key=_idempotency(idempotency_key),
        ),
    )
    return StockOut.model_validate(stock)


@router.post(
    "/reservations",
    response_model=ReservationOut,
    status_code=201,
    summary="Резерв FBS",
    response_description="Созданный резерв (status=ACTIVE).",
)
async def reserve_stock(
    body: ReserveStockRequest,
    uow: UnitOfWork = Depends(get_uow),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> ReservationOut:
    """Резервирует товар под FBS: увеличивает `reserved`, `physical` не меняется.

    При нехватке доступного остатка возвращает 409 с `shortfall` и доступными остатками
    на других складах. Событие домена: `StockReserved`.
    """
    reservation = await ReserveFBSStockUseCase().execute(
        uow,
        ReserveStockCommand(
            warehouse_id=body.warehouse_id,
            product_id=body.product_id,
            quantity=body.quantity,
            idempotency_key=_idempotency(idempotency_key),
        ),
    )
    return ReservationOut.model_validate(reservation)


@router.post(
    "/reservations/{reservation_id}/cancel",
    response_model=ReservationOut,
    summary="Отменить резерв FBS",
    response_description="Резерв в статусе CANCELLED; зарезервированное количество освобождено.",
)
async def cancel_reservation(
    reservation_id: UUID, uow: UnitOfWork = Depends(get_uow)
) -> ReservationOut:
    """Отменяет активный резерв; `physical` не меняется. Событие: `StockReservationCancelled`."""
    reservation = await CancelFBSReservationUseCase().execute(
        uow, CancelReservationCommand(reservation_id=reservation_id)
    )
    return ReservationOut.model_validate(reservation)


@router.post(
    "/transfers",
    response_model=TransferOut,
    status_code=201,
    summary="Создать перемещение",
    response_description="Созданное перемещение в статусе DRAFT.",
)
async def create_transfer(
    body: CreateTransferRequest,
    uow: UnitOfWork = Depends(get_uow),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> TransferOut:
    """Создаёт двухэтапное перемещение между ФФ (ещё не списывает остаток).

    Проверяет доступность на складе-источнике (advisory). Событие: `TransferCreated`.
    """
    transfer = await CreateTransferUseCase().execute(
        uow,
        CreateTransferCommand(
            source_warehouse_id=body.source_warehouse_id,
            target_warehouse_id=body.target_warehouse_id,
            items=[ItemLine(product_id=i.product_id, quantity=i.quantity) for i in body.items],
            idempotency_key=_idempotency(idempotency_key),
        ),
    )
    return TransferOut.model_validate(transfer)


@router.post(
    "/transfers/{transfer_id}/dispatch",
    response_model=TransferOut,
    summary="Отправить перемещение",
    response_description="Перемещение в статусе IN_TRANSIT; остаток источника уменьшен.",
)
async def dispatch_transfer(transfer_id: UUID, uow: UnitOfWork = Depends(get_uow)) -> TransferOut:
    """Списывает товар с источника (под блокировкой) и переводит в статус «в пути».

    Повторный вызов идемпотентен. Событие: `TransferDispatched`.
    """
    transfer = await DispatchTransferUseCase().execute(
        uow, DispatchTransferCommand(transfer_id=transfer_id)
    )
    return TransferOut.model_validate(transfer)


@router.post(
    "/transfers/{transfer_id}/receive",
    response_model=TransferOut,
    summary="Принять перемещение",
    response_description="Перемещение в статусе RECEIVED; остаток цели увеличен.",
)
async def receive_transfer(transfer_id: UUID, uow: UnitOfWork = Depends(get_uow)) -> TransferOut:
    """Принимает товар на целевом складе.

    Повторная приёмка невозможна. Событие: `TransferReceived`.
    """
    transfer = await ReceiveTransferUseCase().execute(
        uow, ReceiveTransferCommand(transfer_id=transfer_id)
    )
    return TransferOut.model_validate(transfer)


@router.post(
    "/shipments/fbs",
    response_model=ShipmentOut,
    status_code=201,
    summary="Отправить FBS (из резерва)",
    response_description="Созданная отправка FBS в статусе SHIPPED.",
)
async def ship_fbs(
    body: ShipFBSRequest,
    uow: UnitOfWork = Depends(get_uow),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> ShipmentOut:
    """Отправляет активный резерв FBS клиенту: уменьшает `physical` и `reserved`.

    Повторная отправка одного резерва не списывает товар дважды. Событие: `FBSOrderShipped`.
    """
    shipment = await ShipFBSOrderUseCase().execute(
        uow,
        ShipFBSCommand(
            reservation_id=body.reservation_id, idempotency_key=_idempotency(idempotency_key)
        ),
    )
    return ShipmentOut.model_validate(shipment)


@router.post(
    "/shipments/fbo",
    response_model=ShipmentOut,
    status_code=201,
    summary="Создать отправку FBO",
    response_description="Созданная отправка FBO в статусе DRAFT.",
)
async def create_fbo(
    body: CreateFBORequest,
    uow: UnitOfWork = Depends(get_uow),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> ShipmentOut:
    """Создаёт отправку на склад Wildberries (FBO), ещё не списывая остаток.

    Событие: `FBOShipmentCreated`.
    """
    shipment = await CreateFBOShipmentUseCase().execute(
        uow,
        CreateFBOShipmentCommand(
            source_warehouse_id=body.source_warehouse_id,
            items=[ItemLine(product_id=i.product_id, quantity=i.quantity) for i in body.items],
            idempotency_key=_idempotency(idempotency_key),
        ),
    )
    return ShipmentOut.model_validate(shipment)


@router.post(
    "/shipments/{shipment_id}/dispatch",
    response_model=ShipmentOut,
    summary="Отправить FBO",
    response_description="Отправка FBO в статусе IN_TRANSIT; остаток источника уменьшен.",
)
async def dispatch_shipment(shipment_id: UUID, uow: UnitOfWork = Depends(get_uow)) -> ShipmentOut:
    """Списывает товар с ФФ и переводит FBO-отправку в «в пути».

    Событие: `FBOShipmentDispatched`.
    """
    shipment = await DispatchFBOShipmentUseCase().execute(
        uow, DispatchShipmentCommand(shipment_id=shipment_id)
    )
    return ShipmentOut.model_validate(shipment)


@router.post(
    "/shipments/{shipment_id}/receive",
    response_model=ShipmentOut,
    summary="Принять FBO на WB",
    response_description="Отправка FBO в статусе RECEIVED.",
)
async def receive_shipment(shipment_id: UUID, uow: UnitOfWork = Depends(get_uow)) -> ShipmentOut:
    """Фиксирует приёмку FBO-отправки на складе Wildberries. Событие: `FBOShipmentReceived`."""
    shipment = await ReceiveFBOShipmentUseCase().execute(
        uow, ReceiveShipmentCommand(shipment_id=shipment_id)
    )
    return ShipmentOut.model_validate(shipment)
