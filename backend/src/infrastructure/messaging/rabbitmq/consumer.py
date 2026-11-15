"""RabbitMQ consumer with manual ack and dead-letter handling."""
from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import Awaitable, Callable
from typing import Any

import aio_pika
from aio_pika import ExchangeType

logger = logging.getLogger("checkstock.rabbitmq.consumer")

Handler = Callable[[dict[str, Any]], Awaitable[None]]


class RabbitMQConsumer:
    def __init__(
        self,
        url: str,
        exchange_name: str,
        queue_name: str,
        dlq_name: str,
        handler: Handler,
        routing_key: str = "#",
    ) -> None:
        self._url = url
        self._exchange_name = exchange_name
        self._queue_name = queue_name
        self._dlq_name = dlq_name
        self._handler = handler
        self._routing_key = routing_key
        self._connection: aio_pika.abc.AbstractRobustConnection | None = None

    async def connect(self) -> None:
        self._connection = await aio_pika.connect_robust(self._url)
        channel = await self._connection.channel()
        await channel.set_qos(prefetch_count=10)

        await channel.declare_exchange(self._exchange_name, ExchangeType.TOPIC, durable=True)
        await channel.declare_exchange("checkstock.dlx", ExchangeType.TOPIC, durable=True)
        await channel.declare_queue(self._dlq_name, durable=True)
        queue = await channel.declare_queue(
            self._queue_name,
            durable=True,
            arguments={
                "x-dead-letter-exchange": "checkstock.dlx",
                "x-dead-letter-routing-key": "dead",
            },
        )
        await queue.bind(self._exchange_name, routing_key=self._routing_key)
        self._queue = queue
        logger.info("consumer connected to queue %s", self._queue_name)

    async def consume(self) -> None:
        if self._queue is None:
            raise RuntimeError("consumer is not connected")
        async with self._queue.iterator() as iterator:
            async for message in iterator:
                async with message.process(requeue=False):
                    try:
                        payload = json.loads(message.body)
                        await self._handler(payload)
                    except Exception:
                        logger.exception("failed to process event; routing to DLQ")
                        raise

    async def close(self) -> None:
        if self._connection is not None:
            await self._connection.close()
            self._connection = None
