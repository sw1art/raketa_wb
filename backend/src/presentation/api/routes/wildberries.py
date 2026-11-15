"""Wildberries integration routes."""
from __future__ import annotations

from fastapi import APIRouter, Depends

from application.use_cases import GetWildberriesStatusUseCase, SyncWildberriesUseCase
from presentation.api.dependencies import get_wb_client, get_wb_sync_logs

router = APIRouter(prefix="/integrations/wb", tags=["wildberries"])


@router.post("/sync")
async def sync_wb(
    client=Depends(get_wb_client), logs=Depends(get_wb_sync_logs)
):
    return await SyncWildberriesUseCase(client, logs).execute()


@router.get("/status")
async def wb_status(
    client=Depends(get_wb_client), logs=Depends(get_wb_sync_logs)
):
    return await GetWildberriesStatusUseCase(client, logs).execute()
