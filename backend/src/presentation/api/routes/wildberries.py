"""Эндпоинты интеграции с Wildberries.

Без токена (`WB_API_TOKEN`) приложение работает в демо-режиме: внутренний учёт
остаётся источником истины, внешние данные WB не перезаписывают физические остатки.
"""

from fastapi import APIRouter, Depends

from application.use_cases import GetWildberriesStatusUseCase, SyncWildberriesUseCase
from presentation.api.dependencies import get_wb_client, get_wb_sync_logs

router = APIRouter(prefix="/integrations/wb", tags=["wildberries"])


@router.post(
    "/sync",
    summary="Синхронизировать с Wildberries",
    response_description="Результат синхронизации (или demo_mode=true при отсутствии токена).",
)
async def sync_wb(client=Depends(get_wb_client), logs=Depends(get_wb_sync_logs)) -> dict:
    """Синхронизирует карточки/заказы/поставки WB и пишет запись в `wb_sync_logs`."""
    return await SyncWildberriesUseCase(client, logs).execute()


@router.get(
    "/status",
    summary="Статус интеграции Wildberries",
    response_description="Настроен ли токен, демо-режим и последняя синхронизация.",
)
async def wb_status(client=Depends(get_wb_client), logs=Depends(get_wb_sync_logs)) -> dict:
    """Возвращает конфигурацию WB и результат последней синхронизации."""
    return await GetWildberriesStatusUseCase(client, logs).execute()
