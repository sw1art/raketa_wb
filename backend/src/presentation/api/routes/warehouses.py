"""Эндпоинты управления складами фулфилмента (ФФ).

Удаление склада — логическое (архивирование): история и остатки сохраняются.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, Query

from application.commands import (
    ArchiveWarehouseCommand,
    CreateWarehouseCommand,
    PurgeWarehouseCommand,
    RenameWarehouseCommand,
)
from application.use_cases import (
    ArchiveWarehouseUseCase,
    CreateWarehouseUseCase,
    GetWarehouseUseCase,
    ListWarehousesUseCase,
    PurgeWarehouseUseCase,
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


@router.get(
    "",
    response_model=list[WarehouseOut],
    summary="Список складов",
    response_description="Список всех складов (или только активных).",
)
async def list_warehouses(
    active_only: bool = Query(
        default=False, description="Только активные (не архивированные) склады"
    ),
    uow: UnitOfWork = Depends(get_uow),
) -> list[WarehouseOut]:
    """Возвращает склады; `active_only=true` скрывает архивированные."""
    warehouses = await ListWarehousesUseCase().execute(uow, active_only=active_only)
    return [WarehouseOut.model_validate(w) for w in warehouses]


@router.get(
    "/{warehouse_id}",
    response_model=WarehouseOut,
    summary="Информация о складе",
    response_description="Данные одного склада.",
)
async def get_warehouse(warehouse_id: UUID, uow: UnitOfWork = Depends(get_uow)) -> WarehouseOut:
    """Возвращает склад по идентификатору; 404, если не найден."""
    warehouse = await GetWarehouseUseCase().execute(uow, warehouse_id)
    return WarehouseOut.model_validate(warehouse)


@router.post(
    "",
    response_model=WarehouseOut,
    status_code=201,
    summary="Создать склад",
    response_description="Созданный склад.",
)
async def create_warehouse(
    body: CreateWarehouseRequest, uow: UnitOfWork = Depends(get_uow)
) -> WarehouseOut:
    """Создаёт новый склад фулфилмента. Имя уникально (409 при дубликате)."""
    warehouse = await CreateWarehouseUseCase().execute(uow, CreateWarehouseCommand(name=body.name))
    return WarehouseOut.model_validate(warehouse)


@router.patch(
    "/{warehouse_id}",
    response_model=WarehouseOut,
    summary="Переименовать склад",
    response_description="Склад с обновлённым названием.",
)
async def rename_warehouse(
    warehouse_id: UUID, body: RenameWarehouseRequest, uow: UnitOfWork = Depends(get_uow)
) -> WarehouseOut:
    """Меняет название склада (логически)."""
    warehouse = await RenameWarehouseUseCase().execute(
        uow, RenameWarehouseCommand(warehouse_id=warehouse_id, name=body.name)
    )
    return WarehouseOut.model_validate(warehouse)


@router.delete(
    "/{warehouse_id}",
    response_model=WarehouseOut,
    summary="Архивировать склад",
    response_description="Архивированный склад (is_active=false).",
)
async def archive_warehouse(warehouse_id: UUID, uow: UnitOfWork = Depends(get_uow)) -> WarehouseOut:
    """Логически архивирует склад.

    Возвращает 409, если у склада есть ненулевые физические остатки, незавершённые
    перемещения/отправки или активные резервы — с перечнем причин и товаров в `detail`.
    """
    warehouse = await ArchiveWarehouseUseCase().execute(
        uow, ArchiveWarehouseCommand(warehouse_id=warehouse_id)
    )
    return WarehouseOut.model_validate(warehouse)


@router.delete(
    "/{warehouse_id}/purge",
    response_model=WarehouseOut,
    summary="Полностью удалить архивный склад",
    response_description="Удалённый склад. 409, если на склад есть ссылки (история сохраняется).",
)
async def purge_warehouse(warehouse_id: UUID, uow: UnitOfWork = Depends(get_uow)) -> WarehouseOut:
    """Физически удаляет уже архивированный склад.

    Допустимо только если склад нигде не использовался (нет остатков, резервов,
    перемещений, отправок, операций и движений) — иначе история будет нарушена.
    """
    warehouse = await PurgeWarehouseUseCase().execute(
        uow, PurgeWarehouseCommand(warehouse_id=warehouse_id)
    )
    return WarehouseOut.model_validate(warehouse)
