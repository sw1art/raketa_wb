"""Wildberries sync-log repository (self-managed session)."""

from __future__ import annotations

from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from application.interfaces import WbSyncLog
from infrastructure.database.models import WbSyncLog as WbSyncLogModel


class WbSyncLogRepository:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def add(self, log: WbSyncLog) -> WbSyncLog:
        async with self._session_factory() as session:
            model = WbSyncLogModel(
                id=uuid4(),
                status=log.status,
                items_processed=log.items_processed,
                error=log.error,
                started_at=log.started_at,
                finished_at=log.finished_at,
            )
            session.add(model)
            await session.commit()
            log.id = model.id
            return log

    async def last(self) -> WbSyncLog | None:
        async with self._session_factory() as session:
            model = await session.scalar(
                select(WbSyncLogModel).order_by(WbSyncLogModel.started_at.desc()).limit(1)
            )
            if model is None:
                return None
            return WbSyncLog(
                id=model.id,
                status=model.status.value if hasattr(model.status, "value") else str(model.status),
                items_processed=model.items_processed,
                error=model.error,
                started_at=model.started_at,
                finished_at=model.finished_at,
            )
