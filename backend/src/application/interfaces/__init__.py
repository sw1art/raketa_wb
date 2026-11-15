"""Application-level interfaces for external dependencies."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Protocol
from uuid import UUID


@dataclass
class WbSyncResult:
    demo_mode: bool = False
    cards_count: int = 0
    fbs_orders_count: int = 0
    external_stocks: list[dict[str, Any]] = field(default_factory=list)
    raw: dict[str, Any] = field(default_factory=dict)


class WildberriesClient(Protocol):
    """Port for the Wildberries adapter."""

    async def sync(self) -> WbSyncResult: ...
    def is_configured(self) -> bool: ...


@dataclass
class WbSyncLog:
    id: UUID | None
    status: str
    items_processed: int
    error: str | None
    started_at: datetime
    finished_at: datetime | None = None


class WbSyncLogRepository(Protocol):
    async def add(self, log: WbSyncLog) -> WbSyncLog: ...
    async def last(self) -> WbSyncLog | None: ...


class ProcessedEventStore(Protocol):
    """Deduplicated event journal (idempotency guard for consumers)."""

    async def record(
        self, consumer_name: str, event_id: str, event_type: str, payload: dict
    ) -> bool: ...
