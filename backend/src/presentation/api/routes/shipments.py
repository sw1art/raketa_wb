"""Эндпоинты просмотра отправок FBS/FBO."""

from fastapi import APIRouter, Depends, Query

from application.commands import ListQuery
from application.use_cases import ListShipmentsUseCase
from domain.enums import ShipmentStatus, ShipmentType
from domain.repositories.interfaces import UnitOfWork
from presentation.api.dependencies import get_uow
from presentation.api.schemas import PaginatedShipments, ShipmentOut

router = APIRouter(prefix="/shipments", tags=["shipments"])


@router.get(
    "",
    response_model=PaginatedShipments,
    summary="Список отправок",
    response_description="Пагинированный список отправок с фильтром по типу и статусу.",
)
async def list_shipments(
    type: str | None = Query(default=None, description="Тип отправки: FBS или FBO"),
    status: str | None = Query(default=None, description="Статус отправки"),
    offset: int = Query(default=0, ge=0, description="Смещение для пагинации"),
    limit: int = Query(default=50, ge=1, le=500, description="Размер страницы (1–500)"),
    uow: UnitOfWork = Depends(get_uow),
) -> PaginatedShipments:
    """Возвращает отправки; невалидные `type`/`status` приводят к ошибке валидации 422."""
    shipment_type = ShipmentType(type) if type else None
    shipment_status = ShipmentStatus(status) if status else None
    shipments, total = await ListShipmentsUseCase().execute(
        uow,
        shipment_type=shipment_type,
        status=shipment_status,
        query=ListQuery(offset=offset, limit=limit),
    )
    return PaginatedShipments(items=[ShipmentOut.model_validate(s) for s in shipments], total=total)
