"""Integration tests for the transactional outbox."""

from __future__ import annotations

import asyncio
from uuid import uuid4

from sqlalchemy import select

from application.commands import ReceiveStockCommand
from application.use_cases import ReceiveStockUseCase
from config.settings import Settings
from domain.enums import OutboxStatus
from domain.events import EVENT_STOCK_RECEIVED
from infrastructure.database.models import OutboxEvent
from infrastructure.outbox.publisher import OutboxPublisher
from infrastructure.repositories.unit_of_work import UnitOfWork

from .helpers import seed_catalog, set_stock


class FakePublisher:
    def __init__(self, fail: bool = False) -> None:
        self.fail = fail
        self.published: list[tuple[str, dict]] = []

    async def publish(self, event_type: str, payload: dict) -> None:
        if self.fail:
            raise RuntimeError("rabbitmq unavailable")
        self.published.append((event_type, payload))


async def _insert_pending_event(session_factory, event_type: str = "StockReceived") -> None:
    async with session_factory() as session:
        session.add(
            OutboxEvent(
                event_id=uuid4(),
                aggregate_type="stock",
                aggregate_id=uuid4(),
                event_type=event_type,
                payload={"event_type": event_type, "event_id": str(uuid4())},
                status=OutboxStatus.PENDING,
            )
        )
        await session.commit()


async def test_receipt_writes_outbox_in_same_transaction(session_factory):
    ids = await seed_catalog(session_factory)
    await set_stock(session_factory, ids["p101"], ids["north"], 10)

    async with session_factory() as session:
        await ReceiveStockUseCase().execute(
            UnitOfWork(session),
            ReceiveStockCommand(warehouse_id=ids["north"], product_id=ids["p101"], quantity=5),
        )

    async with session_factory() as session:
        events = (
            (
                await session.execute(
                    select(OutboxEvent).where(OutboxEvent.event_type == EVENT_STOCK_RECEIVED)
                )
            )
            .scalars()
            .all()
        )
        assert len(events) == 1
        assert events[0].status == OutboxStatus.PENDING


async def test_outbox_publisher_marks_published(session_factory):
    await _insert_pending_event(session_factory)

    fake = FakePublisher()
    settings = Settings(outbox_batch_size=10, outbox_max_retries=2, outbox_retry_base_delay=0.01)
    publisher = OutboxPublisher(session_factory, fake, settings)

    published = await publisher.run_once()
    assert published == 1
    assert len(fake.published) == 1

    async with session_factory() as session:
        events = (await session.execute(select(OutboxEvent))).scalars().all()
        assert events[0].status == OutboxStatus.PUBLISHED
        assert events[0].published_at is not None


async def test_outbox_publisher_retries_on_failure(session_factory):
    await _insert_pending_event(session_factory)

    settings = Settings(outbox_batch_size=10, outbox_max_retries=5, outbox_retry_base_delay=0.01)
    failing = OutboxPublisher(session_factory, FakePublisher(fail=True), settings)
    published = await failing.run_once()
    assert published == 0

    async with session_factory() as session:
        events = (await session.execute(select(OutboxEvent))).scalars().all()
        assert events[0].status == OutboxStatus.PENDING
        assert events[0].retry_count == 1
        assert events[0].next_retry_at is not None

    # Once RabbitMQ "recovers", the event is published.
    await asyncio.sleep(0.05)
    recovering = OutboxPublisher(session_factory, FakePublisher(fail=False), settings)
    published = await recovering.run_once()
    assert published == 1

    async with session_factory() as session:
        events = (await session.execute(select(OutboxEvent))).scalars().all()
        assert events[0].status == OutboxStatus.PUBLISHED
