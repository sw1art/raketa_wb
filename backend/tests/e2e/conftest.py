"""E2E fixtures: run the FastAPI app through an in-process ASGI transport."""

from __future__ import annotations

import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from infrastructure.repositories.unit_of_work import UnitOfWork
from infrastructure.repositories.wb_sync import WbSyncLogRepository
from main import app
from presentation.api.dependencies import get_uow, get_wb_sync_logs


@pytest_asyncio.fixture
async def client(session_factory):
    """HTTP-клиент, тестирующий приложение без реального сетевого сервера.

    Подменяет зависимости `get_uow`/`get_wb_sync_logs`, чтобы запросы работали
    с тестовой базой данных.
    """

    async def override_get_uow():
        async with session_factory() as session:
            yield UnitOfWork(session)

    def override_wb_logs():
        return WbSyncLogRepository(session_factory)

    app.dependency_overrides[get_uow] = override_get_uow
    app.dependency_overrides[get_wb_sync_logs] = override_wb_logs

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c

    app.dependency_overrides.clear()
