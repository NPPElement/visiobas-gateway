from __future__ import annotations

import asyncio
import sys
from json import JSONDecodeError, dumps, loads
from typing import Iterable, Sequence

import asyncio_mqtt
from schemas import BACnetObj

from ..schemas.settings import MQTTSettings
from ..utils import get_file_logger
from .base_client import AbstractBaseClient

_LOG = get_file_logger(name=__name__)

_MQTT_DEFAULT_PORT = 1883


class MQTTClient(AbstractBaseClient):
    """MQTT client."""

    async def init_client(self, settings: MQTTSettings) -> None:
        self._client = asyncio_mqtt.Client(
            hostname=settings.url.host,
            port=settings.url.port or _MQTT_DEFAULT_PORT,
            username=settings.url.user,
            password=settings.url.password,
            client_id=settings.client_id,
            protocol=asyncio_mqtt.ProtocolVersion.V311,
            transport="tcp",
            keepalive=settings.keepalive
            # todo security
        )

    async def _startup_tasks(self) -> None:
        await self._client.connect()
        await self._client.subscribe(self._settings.topics_sub_with_qos)

    async def _shutdown_tasks(self) -> None:
        await self._client.unsubscribe(self._settings.topics_sub_with_qos)
        await self._client.__aexit__(*sys.exc_info())

    @staticmethod
    def objects_to_message(objs: Iterable[BACnetObj]) -> str:
        return "".join([obj.to_mqtt_str(obj=obj) for obj in objs])

    async def send_objects(self, objs: Sequence[BACnetObj]) -> None:
        msg = self.objects_to_message(objs=objs).encode()
        topic = ...  # fixme: create
        await self._scheduler.spawn(
            self._client.publish(topic, msg, self._settings.qos, self._settings.retain)
        )

    # def _on_message_cb(self, client: Any, userdata: Any, message: mqtt.MQTTMessage) -> None:
    #     # todo: type hints
    #     _LOG.debug(
    #         "Received message",
    #         extra={
    #             "topic": message.topic,
    #             "message": message,
    #         },
    #     )
    #     decoded_msg = self._decode(msg=message)
    #
    #     if isinstance(decoded_msg, dict) and decoded_msg.get("jsonrpc") == 2.0:
    #         rpc_task = self._gtw.async_add_job(self.jsonrpc_over_http, decoded_msg)
    #         self._gtw.add_job(self._publish_rpc_response, rpc_task, message.topic)

    async def _publish_rpc_response(self, rpc_task: asyncio.Task, topic: str) -> None:
        rpc_result = await rpc_task
        await self.publish(topic=topic, payload=rpc_result)

    async def jsonrpc_over_http(self, payload: dict) -> str:
        """Performs JSON-RPC over HTTP.

        Args:
            payload:

        Returns:
            RPC Response is successful.
        """
        if self._gtw.http_client is None:
            raise ValueError("HTTP client required")

        text = await self._gtw.http_client.request(
            method="POST",
            url="http://127.0.0.1:7070/json-rpc",
            json=payload,
            headers="application/json",
            extract_text=True,
        )
        if isinstance(text, str):
            return text
        _LOG.warning("Failed JSON-RPC 2.0 over HTTP", extra={"http_response": text})
        return dumps({"jsonrpc": "2.0", "result": {"success": False, "http_status": text}})

    # @staticmethod
    # def _decode(msg: mqtt.MQTTMessage) -> dict | str:
    #     try:
    #         if isinstance(msg.payload, bytes):
    #             content = loads(msg.payload.decode("utf-8", "ignore"))
    #         else:
    #             content = loads(msg.payload)
    #     except JSONDecodeError:
    #         if isinstance(msg.payload, bytes):
    #             content = msg.payload.decode("utf-8", "ignore")
    #         else:
    #             content = msg.payload
    #     return content
