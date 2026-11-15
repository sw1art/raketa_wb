"""Shipment listing routes."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from application.commands import ListQuery
from application.use_cases import ListShipmentsUseCase
from domain.enums import ShipmentStatus, ShipmentType
from domain.repositories.interfaces import UnitOfWork
from presentation.api.dependencies import get_uow
from presentation.api.schemas import PaginatedShipments, ShipmentOut

router = APIRouter(prefix="/shipments", tags=["shipments"])


@router.get("", response_model=PaginatedShipments)
async def list_shipments(
    type: str | None = Query(default=None),
    status: str | None = Query(default=None),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=500),
    uow: UnitOfWork = Depends(get_uow),
):
    shipment_type = ShipmentType(type) if type else None
    shipment_status = ShipmentStatus(status) if status else None
    shipments, total = await ListShipmentsUseCase().execute(
        uow,
        shipment_type=shipment_type,
        status=shipment_status,
        query=ListQuery(offset=offset, limit=limit),
    )
    return PaginatedShipments(
        items=[ShipmentOut.model_validate(s) for s in shipments], total=total
    )
