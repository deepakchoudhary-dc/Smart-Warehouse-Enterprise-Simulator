"""Messaging abstraction supporting MQTT and AMQP backends."""

from __future__ import annotations

import asyncio
import json
import ssl
from dataclasses import dataclass
from typing import Awaitable, Callable, Dict, Optional

import aio_pika
from aio_pika.abc import AbstractIncomingMessage
import paho.mqtt.client as mqtt

from smart_warehouse.enterprise.config.settings import MQTTSettings


MessageHandler = Callable[[dict], Awaitable[None] | None]


@dataclass
class MessageEnvelope:
	"""Represents a structured message transported over the bus."""

	topic: str
	payload: dict
	qos: int = 0


class MessageBus:
	"""Abstract messaging bus interface."""

	async def connect(self) -> None:  # pragma: no cover - interface
		raise NotImplementedError

	async def publish(self, envelope: MessageEnvelope) -> None:  # pragma: no cover - interface
		raise NotImplementedError

	async def subscribe(self, topic: str, handler: MessageHandler) -> None:  # pragma: no cover - interface
		raise NotImplementedError

	async def close(self) -> None:  # pragma: no cover - interface
		raise NotImplementedError


class MQTTMessageBus(MessageBus):
	"""Async wrapper around :mod:`paho.mqtt` with TLS support."""

	def __init__(self, client_id: str, settings: MQTTSettings) -> None:
		self.settings = settings
		self.client = mqtt.Client(client_id=client_id, callback_api_version=mqtt.CallbackAPIVersion.VERSION2)
		self.loop = asyncio.get_event_loop()
		self._subscriptions: Dict[str, MessageHandler] = {}
		self.client.on_message = self._handle_message
		self.client.on_connect = self._on_connect

		if settings.username:
			self.client.username_pw_set(settings.username, settings.password)

		if settings.use_tls:
			context = ssl.create_default_context()
			if settings.ca_path:
				context.load_verify_locations(settings.ca_path)
			if settings.client_cert_path and settings.client_key_path:
				context.load_cert_chain(settings.client_cert_path, settings.client_key_path)
			self.client.tls_set_context(context)

	async def connect(self) -> None:
		await self.loop.run_in_executor(
			None,
			lambda: self.client.connect(self.settings.broker_host, self.settings.port, keepalive=60),
		)
		self.client.loop_start()

	def _on_connect(self, client: mqtt.Client, _userdata, _flags, rc: int, _properties=None) -> None:
		if rc != 0:
			raise ConnectionError(f"MQTT connection failed with code {rc}")
		for topic in self._subscriptions:
			client.subscribe(topic)

	def _handle_message(
		self,
		_client: mqtt.Client,
		_userdata,
		msg: mqtt.MQTTMessage,
	) -> None:
		handler = self._subscriptions.get(msg.topic)
		if not handler:
			return
		payload = json.loads(msg.payload.decode())

		async def invoke() -> None:
			result = handler(payload)
			if asyncio.iscoroutine(result):
				await result

		asyncio.run_coroutine_threadsafe(invoke(), self.loop)

	async def publish(self, envelope: MessageEnvelope) -> None:
		data = json.dumps(envelope.payload)
		await self.loop.run_in_executor(
			None,
			lambda: self.client.publish(envelope.topic, data, qos=envelope.qos),
		)

	async def subscribe(self, topic: str, handler: MessageHandler) -> None:
		self._subscriptions[topic] = handler
		await self.loop.run_in_executor(None, lambda: self.client.subscribe(topic))

	async def close(self) -> None:
		await self.loop.run_in_executor(None, self.client.loop_stop)
		await self.loop.run_in_executor(None, self.client.disconnect)


class AMQPMessageBus(MessageBus):
	"""AMQP implementation backed by :mod:`aio_pika`."""

	def __init__(self, url: str) -> None:
		self.url = url
		self._connection: Optional[aio_pika.RobustConnection] = None
		self._channel: Optional[aio_pika.abc.AbstractChannel] = None
		self._queues: Dict[str, aio_pika.abc.AbstractQueue] = {}

	async def connect(self) -> None:
		self._connection = await aio_pika.connect_robust(self.url)
		self._channel = await self._connection.channel()

	async def publish(self, envelope: MessageEnvelope) -> None:
		if not self._channel:
			raise RuntimeError("AMQP channel not initialised")
		exchange = await self._channel.declare_exchange("smart_warehouse", aio_pika.ExchangeType.TOPIC)
		await exchange.publish(
			aio_pika.Message(body=json.dumps(envelope.payload).encode()),
			routing_key=envelope.topic,
		)

	async def subscribe(self, topic: str, handler: MessageHandler) -> None:
		if not self._channel:
			raise RuntimeError("AMQP channel not initialised")
		queue = await self._channel.declare_queue(topic, durable=False, auto_delete=True)
		await queue.bind("smart_warehouse", routing_key=topic)

		async def _wrapped(message: AbstractIncomingMessage) -> None:
			async with message.process():
				payload = json.loads(message.body.decode())
				result = handler(payload)
				if asyncio.iscoroutine(result):
					await result

		await queue.consume(_wrapped)
		self._queues[topic] = queue

	async def close(self) -> None:
		if self._channel:
			await self._channel.close()
		if self._connection:
			await self._connection.close()
