"""Эндпоинты истории операций."""

from uuid import UUID

from fastapi import APIRouter, Depends, Query

from application.commands import ListQuery
from application.use_cases import GetHistoryUseCase, ListHistoryUseCase
from domain.repositories.interfaces import UnitOfWork
from presentation.api.dependencies import get_uow
from presentation.api.schemas import HistoryEntryOut, PaginatedHistory

router = APIRouter(prefix="/history", tags=["history"])


@router.get(
    "",
    response_model=PaginatedHistory,
    summary="История операций",
    response_description="Пагинированная история операций с фильтром по типу и SKU.",
)
async def list_history(
    operation_type: str | None = Query(default=None, description="Тип операции (например RECEIPT)"),
    sku: str | None = Query(default=None, description="Фильтр по SKU (подстрока)"),
    offset: int = Query(default=0, ge=0, description="Смещение для пагинации"),
    limit: int = Query(default=50, ge=1, le=500, description="Размер страницы (1–500)"),
    uow: UnitOfWork = Depends(get_uow),
) -> PaginatedHistory:
    """Возвращает неизменяемый журнал операций: что, сколько, откуда, куда и когда."""
    entries, total = await ListHistoryUseCase().execute(
        uow,
        operation_type=operation_type,
        sku=sku,
        query=ListQuery(offset=offset, limit=limit),
    )
    return PaginatedHistory(items=[HistoryEntryOut.model_validate(e) for e in entries], total=total)


@router.get(
    "/{operation_id}",
    response_model=list[HistoryEntryOut],
    summary="Детали операции",
    response_description="Строки истории одной операции.",
)
async def get_history(
    operation_id: UUID, uow: UnitOfWork = Depends(get_uow)
) -> list[HistoryEntryOut]:
    """Возвращает все записи (строки) одной операции; 404, если операция не найдена."""
    entries = await GetHistoryUseCase().execute(uow, operation_id)
    return [HistoryEntryOut.model_validate(e) for e in entries]
