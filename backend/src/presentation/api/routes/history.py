"""History routes."""
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query

from application.commands import ListQuery
from application.use_cases import GetHistoryUseCase, ListHistoryUseCase
from domain.repositories.interfaces import UnitOfWork
from presentation.api.dependencies import get_uow
from presentation.api.schemas import HistoryEntryOut, PaginatedHistory

router = APIRouter(prefix="/history", tags=["history"])


@router.get("", response_model=PaginatedHistory)
async def list_history(
    operation_type: str | None = Query(default=None),
    sku: str | None = Query(default=None),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=500),
    uow: UnitOfWork = Depends(get_uow),
):
    entries, total = await ListHistoryUseCase().execute(
        uow,
        operation_type=operation_type,
        sku=sku,
        query=ListQuery(offset=offset, limit=limit),
    )
    return PaginatedHistory(
        items=[HistoryEntryOut.model_validate(e) for e in entries], total=total
    )


@router.get("/{operation_id}", response_model=list[HistoryEntryOut])
async def get_history(operation_id: UUID, uow: UnitOfWork = Depends(get_uow)):
    entries = await GetHistoryUseCase().execute(uow, operation_id)
    return [HistoryEntryOut.model_validate(e) for e in entries]
