"""Application-level event handlers."""
from __future__ import annotations

import logging
from uuid import UUID

from ..interfaces import ProcessedEventStore

logger = logging.getLogger("checkstock.consumer")


class EventJournalHandler:
    """Persists consumed events into a deduplicated journal.

    Idempotency is guaranteed by the store's unique constraint on
    (consumer_name, event_id): re-deliveries become no-ops.
    """

    def __init__(self, store: ProcessedEventStore, consumer_name: str) -> None:
        self._store = store
        self._consumer_name = consumer_name

    async def handle(self, payload: dict) -> None:
        event_id = payload.get("event_id")
        event_type = payload.get("event_type", "unknown")
        if not event_id:
            logger.warning("event without event_id skipped")
            return
        recorded = await self._store.record(
            consumer_name=self._consumer_name,
            event_id=str(UUID(event_id)),
            event_type=event_type,
            payload=payload,
        )
        if recorded:
            logger.info(
                "journaled event",
                extra={"event": event_type, "consumer": self._consumer_name},
            )
