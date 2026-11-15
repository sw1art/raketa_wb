"""Эндпоинты листингов резервов и перемещений (для управления операциями)."""

from fastapi import APIRouter, Depends, Query

from application.use_cases import ListReservationsUseCase, ListTransfersUseCase
from domain.repositories.interfaces import UnitOfWork
from presentation.api.dependencies import get_uow
from presentation.api.schemas import ReservationViewOut, TransferViewOut

router = APIRouter(tags=["operations"])


@router.get(
    "/reservations",
    response_model=list[ReservationViewOut],
    summary="Список резервов",
    response_description="Резервы с названиями товара и склада (фильтр по статусу).",
)
async def list_reservations(
    status: str | None = Query(default=None, description="Фильтр по статусу (например ACTIVE)"),
    uow: UnitOfWork = Depends(get_uow),
) -> list[ReservationViewOut]:
    """Возвращает резервы; `status=ACTIVE` — активные резервы для отправки/отмены FBS."""
    items = await ListReservationsUseCase().execute(uow, status=status)
    return [ReservationViewOut.model_validate(r) for r in items]


@router.get(
    "/transfers",
    response_model=list[TransferViewOut],
    summary="Список перемещений",
    response_description="Перемещения с именами складов и строками товаров.",
)
async def list_transfers(
    status: str | None = Query(
        default=None, description="Фильтр по статусу (DRAFT, IN_TRANSIT, RECEIVED)"
    ),
    uow: UnitOfWork = Depends(get_uow),
) -> list[TransferViewOut]:
    """Возвращает перемещения для отправки/приёмки."""
    items = await ListTransfersUseCase().execute(uow, status=status)
    return [TransferViewOut.model_validate(t) for t in items]
