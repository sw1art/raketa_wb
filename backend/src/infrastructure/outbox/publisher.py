"""Transactional Outbox publisher."""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from config.settings import Settings
from domain.enums import OutboxStatus
from infrastructure.database.models import OutboxEvent
from infrastructure.messaging.rabbitmq.publisher import RabbitMQPublisher

logger = logging.getLogger("checkstock.outbox")


def _now() -> datetime:
    return datetime.now(timezone.utc)


class OutboxPublisher:
    """Relays outbox events to RabbitMQ with publisher confirms.

    A batch of PENDING events is claimed with `FOR UPDATE SKIP LOCKED` so that
    multiple worker instances can run concurrently without double-publishing.
    """

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        publisher: RabbitMQPublisher,
        settings: Settings,
    ) -> None:
        self._session_factory = session_factory
        self._publisher = publisher
        self._batch_size = settings.outbox_batch_size
        self._max_retries = settings.outbox_max_retries
        self._base_delay = settings.outbox_retry_base_delay

    async def run_once(self) -> int:
        published = 0
        async with self._session_factory() as session:
            rows = await session.scalars(
                select(OutboxEvent)
                .where(
                    OutboxEvent.status == OutboxStatus.PENDING,
                    (OutboxEvent.next_retry_at.is_(None))
                    | (OutboxEvent.next_retry_at <= _now()),
                )
                .order_by(OutboxEvent.created_at, OutboxEvent.id)
                .limit(self._batch_size)
                .with_for_update(skip_locked=True)
            )
            events = list(rows)
            for event in events:
                try:
                    await self._publisher.publish(event.event_type, event.payload)
                    event.status = OutboxStatus.PUBLISHED
                    event.published_at = _now()
                    event.last_error = None
                    published += 1
                except Exception as exc:  # transient error -> retry with backoff
                    event.retry_count += 1
                    event.last_error = str(exc)[:2000]
                    if event.retry_count >= self._max_retries:
                        event.status = OutboxStatus.FAILED
                    else:
                        delay = self._base_delay * (2 ** (event.retry_count - 1))
                        event.next_retry_at = _now() + timedelta(seconds=delay)
                    logger.warning(
                        "failed to publish event %s (attempt %d): %s",
                        event.event_type,
                        event.retry_count,
                        exc,
                    )
            await session.commit()
        return published

    async def run_forever(self, poll_interval: float) -> None:
        while True:
            try:
                published = await self.run_once()
                if published:
                    logger.info("published %d outbox events", published)
            except Exception:
                logger.exception("outbox relay iteration failed")
            await asyncio.sleep(poll_interval)
