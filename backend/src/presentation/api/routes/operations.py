"""Operation routes: receipt, reservations, transfers, shipments."""
from __future__ import annotations

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
    return value if value else None


@router.post("/receipts", response_model=StockOut, status_code=201)
async def receive_stock(
    body: ReceiveStockRequest,
    uow: UnitOfWork = Depends(get_uow),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
):
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


@router.post("/reservations", response_model=ReservationOut, status_code=201)
async def reserve_stock(
    body: ReserveStockRequest,
    uow: UnitOfWork = Depends(get_uow),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
):
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


@router.post("/reservations/{reservation_id}/cancel", response_model=ReservationOut)
async def cancel_reservation(
    reservation_id: UUID, uow: UnitOfWork = Depends(get_uow)
):
    reservation = await CancelFBSReservationUseCase().execute(
        uow, CancelReservationCommand(reservation_id=reservation_id)
    )
    return ReservationOut.model_validate(reservation)


@router.post("/transfers", response_model=TransferOut, status_code=201)
async def create_transfer(
    body: CreateTransferRequest,
    uow: UnitOfWork = Depends(get_uow),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
):
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


@router.post("/transfers/{transfer_id}/dispatch", response_model=TransferOut)
async def dispatch_transfer(transfer_id: UUID, uow: UnitOfWork = Depends(get_uow)):
    transfer = await DispatchTransferUseCase().execute(
        uow, DispatchTransferCommand(transfer_id=transfer_id)
    )
    return TransferOut.model_validate(transfer)


@router.post("/transfers/{transfer_id}/receive", response_model=TransferOut)
async def receive_transfer(transfer_id: UUID, uow: UnitOfWork = Depends(get_uow)):
    transfer = await ReceiveTransferUseCase().execute(
        uow, ReceiveTransferCommand(transfer_id=transfer_id)
    )
    return TransferOut.model_validate(transfer)


@router.post("/shipments/fbs", response_model=ShipmentOut, status_code=201)
async def ship_fbs(
    body: ShipFBSRequest,
    uow: UnitOfWork = Depends(get_uow),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
):
    shipment = await ShipFBSOrderUseCase().execute(
        uow, ShipFBSCommand(reservation_id=body.reservation_id, idempotency_key=_idempotency(idempotency_key))
    )
    return ShipmentOut.model_validate(shipment)


@router.post("/shipments/fbo", response_model=ShipmentOut, status_code=201)
async def create_fbo(
    body: CreateFBORequest,
    uow: UnitOfWork = Depends(get_uow),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
):
    shipment = await CreateFBOShipmentUseCase().execute(
        uow,
        CreateFBOShipmentCommand(
            source_warehouse_id=body.source_warehouse_id,
            items=[ItemLine(product_id=i.product_id, quantity=i.quantity) for i in body.items],
            idempotency_key=_idempotency(idempotency_key),
        ),
    )
    return ShipmentOut.model_validate(shipment)


@router.post("/shipments/{shipment_id}/dispatch", response_model=ShipmentOut)
async def dispatch_shipment(shipment_id: UUID, uow: UnitOfWork = Depends(get_uow)):
    shipment = await DispatchFBOShipmentUseCase().execute(
        uow, DispatchShipmentCommand(shipment_id=shipment_id)
    )
    return ShipmentOut.model_validate(shipment)


@router.post("/shipments/{shipment_id}/receive", response_model=ShipmentOut)
async def receive_shipment(shipment_id: UUID, uow: UnitOfWork = Depends(get_uow)):
    shipment = await ReceiveFBOShipmentUseCase().execute(
        uow, ReceiveShipmentCommand(shipment_id=shipment_id)
    )
    return ShipmentOut.model_validate(shipment)
