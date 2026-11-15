"""RabbitMQ publisher with publisher confirms."""
from __future__ import annotations

import json
import logging
from typing import Any

import aio_pika
from aio_pika import DeliveryMode, ExchangeType, Message

logger = logging.getLogger("checkstock.rabbitmq.publisher")


class RabbitMQPublisher:
    def __init__(self, url: str, exchange_name: str) -> None:
        self._url = url
        self._exchange_name = exchange_name
        self._connection: aio_pika.abc.AbstractRobustConnection | None = None
        self._exchange: aio_pika.abc.AbstractExchange | None = None

    async def connect(self) -> None:
        self._connection = await aio_pika.connect_robust(self._url)
        # aio-pika 9.x enables publisher confirms by default on channels.
        channel = await self._connection.channel()
        self._exchange = await channel.declare_exchange(
            self._exchange_name, ExchangeType.TOPIC, durable=True
        )
        logger.info("connected to RabbitMQ, exchange %s", self._exchange_name)

    async def publish(self, event_type: str, payload: dict[str, Any]) -> None:
        if self._exchange is None:
            raise RuntimeError("publisher is not connected")
        body = json.dumps(payload, ensure_ascii=False).encode()
        message = Message(
            body=body,
            content_type="application/json",
            delivery_mode=DeliveryMode.PERSISTENT,
        )
        # Blocks until the broker confirms the message (raises on nack).
        await self._exchange.publish(message, routing_key=event_type)

    async def close(self) -> None:
        if self._connection is not None:
            await self._connection.close()
            self._connection = None
            self._exchange = None
