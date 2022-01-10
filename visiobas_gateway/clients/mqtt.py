from __future__ import annotations

import sys
from json import JSONDecodeError, loads  # dumps,
from typing import TYPE_CHECKING, Any, Iterable

import asyncio_mqtt  # type: ignore
from paho.mqtt.client import MQTTMessage  # type: ignore

from ..schemas import BACnetObj
from ..schemas.send_methods import SendMethod
from ..schemas.settings import MQTTSettings
from ..utils import get_file_logger
from .base_client import AbstractBaseClient

if TYPE_CHECKING:
    from ..gateway import Gateway
else:
    Gateway = Any

_LOG = get_file_logger(name=__name__)

_MQTT_DEFAULT_PORT = 1883


class MQTTClient(AbstractBaseClient):
    """MQTT client."""

    def __init__(self, gateway: Gateway, settings: MQTTSettings):
        super().__init__(gateway, settings)
        # Ignore types because always used SecretUrl schema in MQTTSettings
        self._client = asyncio_mqtt.Client(
            hostname=settings.url.host,
            port=settings.url.port,  # type: ignore
            username=settings.url.user.get_secret_value(),  # type: ignore
            password=settings.url.password.get_secret_value(),  # type: ignore
            client_id=settings.client_id,
            protocol=asyncio_mqtt.ProtocolVersion.V311,
            transport="tcp",
            keepalive=settings.keepalive
            # todo security
        )

    def get_send_method(self) -> SendMethod:
        return SendMethod.MQTT

    async def async_init_client(self, settings: MQTTSettings) -> None:
        pass

    async def _startup_tasks(self) -> None:
        await self._client.connect()
        await self._client.subscribe(self._settings.topics_sub_with_qos)
        await self._scheduler.spawn(self.process_messages())

    async def _shutdown_tasks(self) -> None:
        await self._client.unsubscribe(self._settings.topics_sub_with_qos)
        await self._client.__aexit__(*sys.exc_info())

    def objects_to_message(self, objs: Iterable[BACnetObj]) -> str:
        return "".join(
            [
                obj.to_mqtt_str(obj=obj)
                for obj in objs
                if self.get_send_method() in obj.property_list.send_methods
            ]
        )

    async def send_objects(self, objs: Iterable[BACnetObj]) -> None:
        msg = self.objects_to_message(objs=objs).encode()
        topic = ...  # fixme: create
        await self._client.publish(topic, msg, self._settings.qos, self._settings.retain)

    async def process_messages(self) -> None:
        async with self._client.unfiltered_messages() as messages:
            async for msg in messages:
                await self.process_message(message=msg)

    async def process_message(self, message: MQTTMessage) -> None:
        _LOG.debug("Received message", extra={"topic": message.topic, "message": message})
        # decoded_payload = self._decode_payload(message=message)
        ...  # todo

    # def _on_message_cb(self, client: Any, userdata, message: mqtt.MQTTMessage) -> None:

    #     decoded_msg = self._decode(msg=message)
    #
    #     if isinstance(decoded_msg, dict) and decoded_msg.get("jsonrpc") == 2.0:
    #         rpc_task = self._gtw.async_add_job(self.jsonrpc_over_http, decoded_msg)
    #         self._gtw.add_job(self._publish_rpc_response, rpc_task, message.topic)

    # async def _publish_rpc_response(self, rpc_task: asyncio.Task, topic: str) -> None:
    #     rpc_result = await rpc_task
    #     await self.publish(topic=topic, payload=rpc_result)

    # async def jsonrpc_over_http(self, payload: dict) -> str:
    #     """Performs JSON-RPC over HTTP.
    #
    #     Args:
    #         payload:
    #
    #     Returns:
    #         RPC Response is successful.
    #     """
    #     if self._gtw.http_client is None:
    #         raise ValueError("HTTP client required")
    #
    #     text = await self._gtw.http_client.request(
    #         method="POST",
    #         url="http://127.0.0.1:7070/json-rpc",
    #         json=payload,
    #         headers="application/json",
    #         extract_text=True,
    #     )
    #     if isinstance(text, str):
    #         return text
    #     _LOG.warning("Failed JSON-RPC 2.0 over HTTP", extra={"http_response": text})
    #     return dumps(
    #     {"jsonrpc": "2.0", "result": {"success": False, "http_status": text}})

    @staticmethod
    def _decode_payload(message: MQTTMessage) -> dict | str:
        try:
            if isinstance(message.payload, bytes):
                content = loads(message.payload.decode("utf-8", "ignore"))
            else:
                content = loads(message.payload)
        except JSONDecodeError:
            if isinstance(message.payload, bytes):
                content = message.payload.decode("utf-8", "ignore")
            else:
                content = message.payload
        return content
