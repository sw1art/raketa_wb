"""Operations history use cases."""

from __future__ import annotations

from uuid import UUID

from domain.entities import HistoryEntry
from domain.repositories.interfaces import UnitOfWork

from ..commands import ListQuery
from ..exceptions import NotFoundError
from .base import UseCase


class ListHistoryUseCase(UseCase):
    async def _run(
        self,
        uow: UnitOfWork,
        *,
        operation_type: str | None = None,
        sku: str | None = None,
        query: ListQuery,
    ) -> tuple[list[HistoryEntry], int]:
        return await uow.operations.list_history(
            operation_type=operation_type,
            sku=sku,
            offset=query.offset,
            limit=query.limit,
        )


class GetHistoryUseCase(UseCase):
    async def _run(self, uow: UnitOfWork, operation_id: UUID) -> list[HistoryEntry]:
        entries = await uow.operations.get_history(operation_id)
        if not entries:
            raise NotFoundError(f"operation {operation_id} not found")
        return entries
