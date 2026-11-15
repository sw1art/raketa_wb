"""Reservation and transfer listing routes."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from application.use_cases import ListReservationsUseCase, ListTransfersUseCase
from domain.repositories.interfaces import UnitOfWork
from presentation.api.dependencies import get_uow
from presentation.api.schemas import ReservationViewOut, TransferViewOut

router = APIRouter(tags=["catalog"])


@router.get("/reservations", response_model=list[ReservationViewOut])
async def list_reservations(
    status: str | None = Query(default=None),
    uow: UnitOfWork = Depends(get_uow),
):
    items = await ListReservationsUseCase().execute(uow, status=status)
    return [ReservationViewOut.model_validate(r) for r in items]


@router.get("/transfers", response_model=list[TransferViewOut])
async def list_transfers(
    status: str | None = Query(default=None),
    uow: UnitOfWork = Depends(get_uow),
):
    items = await ListTransfersUseCase().execute(uow, status=status)
    return [TransferViewOut.model_validate(t) for t in items]
