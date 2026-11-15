"""Processed-events store (idempotency guard) implementation."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from infrastructure.database.models import ProcessedEvent


class ProcessedEventStore:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def record(
        self, consumer_name: str, event_id: str, event_type: str, payload: dict
    ) -> bool:
        async with self._session_factory() as session:
            stmt = (
                pg_insert(ProcessedEvent)
                .values(
                    consumer_name=consumer_name,
                    event_id=event_id,
                    event_type=event_type,
                    payload=payload,
                )
                .on_conflict_do_nothing(
                    index_elements=[ProcessedEvent.consumer_name, ProcessedEvent.event_id]
                )
                .returning(ProcessedEvent.id)
            )
            result = await session.scalar(stmt)
            await session.commit()
            return result is not None
