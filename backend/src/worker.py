"""Background worker: outbox publisher + event-journal consumer."""

from __future__ import annotations

import asyncio
import logging

from application.handlers import EventJournalHandler
from config.logging import configure_logging
from config.settings import get_settings
from infrastructure.database.session import SessionFactory
from infrastructure.messaging.rabbitmq.consumer import RabbitMQConsumer
from infrastructure.messaging.rabbitmq.publisher import RabbitMQPublisher
from infrastructure.outbox.publisher import OutboxPublisher
from infrastructure.repositories.processed_events import ProcessedEventStore

logger = logging.getLogger("checkstock.worker")


async def _run_publisher(publisher: OutboxPublisher, interval: float) -> None:
    await publisher.run_forever(interval)


async def _run_consumer(consumer: RabbitMQConsumer) -> None:
    while True:
        try:
            await consumer.consume()
        except Exception:
            logger.exception("consumer loop error; reconnecting")
            await asyncio.sleep(5)


async def run() -> None:
    settings = get_settings()

    rabbit_publisher = RabbitMQPublisher(settings.rabbitmq_url, settings.rabbitmq_exchange)
    outbox = OutboxPublisher(SessionFactory, rabbit_publisher, settings)

    event_store = ProcessedEventStore(SessionFactory)
    handler = EventJournalHandler(event_store, settings.rabbitmq_consumer_name)
    consumer = RabbitMQConsumer(
        settings.rabbitmq_url,
        settings.rabbitmq_exchange,
        settings.rabbitmq_queue,
        settings.rabbitmq_dlq,
        handler.handle,
    )

    # Wait until RabbitMQ is reachable.
    while True:
        try:
            await rabbit_publisher.connect()
            await consumer.connect()
            break
        except Exception:
            logger.warning("RabbitMQ not ready, retrying in 5s")
            await asyncio.sleep(5)

    consumer_task = asyncio.create_task(_run_consumer(consumer))
    await _run_publisher(outbox, settings.outbox_poll_interval)
    await consumer_task


def main() -> None:
    settings = get_settings()
    configure_logging(settings.log_level)
    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        logger.info("worker stopped")


if __name__ == "__main__":
    main()
