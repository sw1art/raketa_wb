"""FastAPI dependencies."""

from __future__ import annotations

from collections.abc import AsyncIterator

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from config.settings import get_settings
from infrastructure.database.session import SessionFactory, get_session
from infrastructure.integrations.wildberries.client import WildberriesClient
from infrastructure.repositories.unit_of_work import UnitOfWork
from infrastructure.repositories.wb_sync import WbSyncLogRepository

_settings = get_settings()


async def get_uow(session: AsyncSession = Depends(get_session)) -> AsyncIterator[UnitOfWork]:
    uow = UnitOfWork(session)
    try:
        yield uow
    finally:
        await uow.close()


def get_wb_client() -> WildberriesClient:
    return WildberriesClient(_settings)


def get_wb_sync_logs() -> WbSyncLogRepository:
    return WbSyncLogRepository(SessionFactory)
