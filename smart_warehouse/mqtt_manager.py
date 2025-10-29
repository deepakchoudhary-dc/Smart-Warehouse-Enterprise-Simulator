"""MQTT client wrapper honouring enterprise messaging settings."""

from __future__ import annotations

import json
import ssl
from typing import Callable

import paho.mqtt.client as mqtt

from smart_warehouse.enterprise.config.settings import AppSettings, MQTTSettings, get_settings


class MQTTManager:
    """Manages MQTT connection for broadcasting and receiving cell reservations."""

    def __init__(
        self,
        agent_id: str,
        reservation_callback: Callable[[str, int, int], None],
        settings: AppSettings | None = None,
    ) -> None:
        self.agent_id = agent_id
        self.reservation_callback = reservation_callback
        self.settings = settings or get_settings()
        self.mqtt_settings: MQTTSettings = self.settings.mqtt

        self.client = mqtt.Client(client_id=agent_id, callback_api_version=mqtt.CallbackAPIVersion.VERSION2)
        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message

        if self.mqtt_settings.username:
            self.client.username_pw_set(self.mqtt_settings.username, self.mqtt_settings.password)

        if self.mqtt_settings.use_tls:
            context = ssl.create_default_context()
            if self.mqtt_settings.ca_path:
                context.load_verify_locations(self.mqtt_settings.ca_path)
            if self.mqtt_settings.client_cert_path and self.mqtt_settings.client_key_path:
                context.load_cert_chain(
                    certfile=self.mqtt_settings.client_cert_path,
                    keyfile=self.mqtt_settings.client_key_path,
                )
            self.client.tls_set_context(context)

    def connect(self) -> None:
        """Connects to the MQTT broker and starts the network loop."""

        try:
            self.client.connect(self.mqtt_settings.broker_host, self.mqtt_settings.port, 60)
            self.client.loop_start()
        except Exception as exc:  # pragma: no cover - guarded for runtime visibility
            print(f"[{self.agent_id}] MQTT connection failed: {exc}")

    def _on_connect(self, client: mqtt.Client, _userdata, _flags, rc: int, _properties=None) -> None:
        if rc == 0:
            print(f"[{self.agent_id}] Connected to MQTT broker.")
            client.subscribe(self.mqtt_settings.topic_reservations)
        else:  # pragma: no cover - connection failures do not occur in happy-path tests
            print(f"[{self.agent_id}] Failed to connect, return code {rc}")

    def _on_message(self, _client: mqtt.Client, _userdata, msg: mqtt.MQTTMessage) -> None:
        try:
            payload = json.loads(msg.payload.decode())
            if payload.get("agent_id") != self.agent_id:
                self.reservation_callback(payload["agent_id"], payload["x"], payload["y"])
        except Exception as exc:  # pragma: no cover - guarding parse errors only
            print(f"[{self.agent_id}] Error processing message: {exc}")

    def publish_reservation(self, x: int, y: int) -> None:
        """Broadcast that this agent is reserving a cell."""

        payload = {"agent_id": self.agent_id, "x": x, "y": y}
        self.client.publish(self.mqtt_settings.topic_reservations, json.dumps(payload))

    def disconnect(self) -> None:
        self.client.loop_stop()
        self.client.disconnect()
