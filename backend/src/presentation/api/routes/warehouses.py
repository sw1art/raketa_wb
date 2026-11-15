"""Warehouse routes."""
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query

from application.commands import (
    ArchiveWarehouseCommand,
    CreateWarehouseCommand,
    RenameWarehouseCommand,
)
from application.use_cases import (
    ArchiveWarehouseUseCase,
    CreateWarehouseUseCase,
    GetWarehouseUseCase,
    ListWarehousesUseCase,
    RenameWarehouseUseCase,
)
from domain.repositories.interfaces import UnitOfWork
from presentation.api.dependencies import get_uow
from presentation.api.schemas import (
    CreateWarehouseRequest,
    RenameWarehouseRequest,
    WarehouseOut,
)

router = APIRouter(prefix="/warehouses", tags=["warehouses"])


@router.get("", response_model=list[WarehouseOut])
async def list_warehouses(
    active_only: bool = Query(default=False),
    uow: UnitOfWork = Depends(get_uow),
):
    warehouses = await ListWarehousesUseCase().execute(uow, active_only=active_only)
    return [WarehouseOut.model_validate(w) for w in warehouses]


@router.get("/{warehouse_id}", response_model=WarehouseOut)
async def get_warehouse(warehouse_id: UUID, uow: UnitOfWork = Depends(get_uow)):
    warehouse = await GetWarehouseUseCase().execute(uow, warehouse_id)
    return WarehouseOut.model_validate(warehouse)


@router.post("", response_model=WarehouseOut, status_code=201)
async def create_warehouse(
    body: CreateWarehouseRequest, uow: UnitOfWork = Depends(get_uow)
):
    warehouse = await CreateWarehouseUseCase().execute(
        uow, CreateWarehouseCommand(name=body.name)
    )
    return WarehouseOut.model_validate(warehouse)


@router.patch("/{warehouse_id}", response_model=WarehouseOut)
async def rename_warehouse(
    warehouse_id: UUID, body: RenameWarehouseRequest, uow: UnitOfWork = Depends(get_uow)
):
    warehouse = await RenameWarehouseUseCase().execute(
        uow, RenameWarehouseCommand(warehouse_id=warehouse_id, name=body.name)
    )
    return WarehouseOut.model_validate(warehouse)


@router.delete("/{warehouse_id}", response_model=WarehouseOut)
async def archive_warehouse(warehouse_id: UUID, uow: UnitOfWork = Depends(get_uow)):
    warehouse = await ArchiveWarehouseUseCase().execute(
        uow, ArchiveWarehouseCommand(warehouse_id=warehouse_id)
    )
    return WarehouseOut.model_validate(warehouse)
