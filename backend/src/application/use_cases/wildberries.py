"""Wildberries integration use cases."""
from __future__ import annotations

from datetime import datetime, timezone

from domain.enums import WbSyncStatus

from ..interfaces import WbSyncLog, WbSyncLogRepository, WildberriesClient


class SyncWildberriesUseCase:
    def __init__(
        self,
        client: WildberriesClient,
        sync_logs: WbSyncLogRepository,
    ) -> None:
        self._client = client
        self._sync_logs = sync_logs

    async def execute(self) -> dict:
        started = datetime.now(timezone.utc)
        if not self._client.is_configured():
            await self._sync_logs.add(
                WbSyncLog(
                    id=None,
                    status=WbSyncStatus.DEMO,
                    items_processed=0,
                    error=None,
                    started_at=started,
                    finished_at=started,
                )
            )
            return {
                "status": WbSyncStatus.DEMO,
                "demo_mode": True,
                "message": "WB token is not configured; running in local demo mode",
            }

        try:
            result = await self._client.sync()
            status = WbSyncStatus.SUCCESS
            items = result.cards_count + result.fbs_orders_count
            error = None
        except Exception as exc:  # pragma: no cover - adapter handles most errors
            status = WbSyncStatus.FAILED
            items = 0
            error = str(exc)

        await self._sync_logs.add(
            WbSyncLog(
                id=None,
                status=status,
                items_processed=items,
                error=error,
                started_at=started,
                finished_at=datetime.now(timezone.utc),
            )
        )
        return {
            "status": status,
            "demo_mode": False,
            "items_processed": items,
            "error": error,
        }


class GetWildberriesStatusUseCase:
    def __init__(self, client: WildberriesClient, sync_logs: WbSyncLogRepository) -> None:
        self._client = client
        self._sync_logs = sync_logs

    async def execute(self) -> dict:
        last = await self._sync_logs.last()
        return {
            "configured": self._client.is_configured(),
            "demo_mode": not self._client.is_configured(),
            "last_sync": (
                {
                    "status": last.status,
                    "items_processed": last.items_processed,
                    "error": last.error,
                    "started_at": last.started_at.isoformat() if last.started_at else None,
                    "finished_at": last.finished_at.isoformat() if last.finished_at else None,
                }
                if last
                else None
            ),
        }
