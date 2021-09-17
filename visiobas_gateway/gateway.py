from __future__ import annotations

import asyncio
from typing import (
    TYPE_CHECKING,
    Any,
    Awaitable,
    Callable,
    Collection,
    Optional,
    Type,
    Union,
)

import aiohttp
import aiojobs  # type: ignore

from visiobas_gateway.api import ApiServer
from visiobas_gateway.clients import HTTPClient, MQTTClient
from visiobas_gateway.devices import BACnetDevice, ModbusDevice, SUNAPIDevice
from visiobas_gateway.devices._base_polling_device import BasePollingDevice
from visiobas_gateway.schemas.bacnet import BACnetObj, DeviceObj, ObjType
from visiobas_gateway.schemas.bacnet.device_obj import POLLING_TYPES
from visiobas_gateway.schemas.modbus import ModbusObj
from visiobas_gateway.schemas.protocol import POLLING_PROTOCOLS, Protocol
from visiobas_gateway.schemas.settings import (
    ApiSettings,
    GatewaySettings,
    HTTPSettings,
    MQTTSettings,
)
from visiobas_gateway.utils import get_file_logger, log_exceptions
from visiobas_gateway.verifier import BACnetVerifier

if TYPE_CHECKING:
    from .devices._base_device import BaseDevice

else:
    BaseDevice = "BaseDevice"

_LOG = get_file_logger(name=__name__)

Object = Union[BACnetObj, ModbusObj]


class Gateway:
    """VisioBAS IoT Gateway."""

    # pylint: disable=too-many-instance-attributes

    def __init__(self, settings: GatewaySettings):
        self.loop: asyncio.AbstractEventLoop = asyncio.get_running_loop()

        # self._pending_tasks: list = []
        self.settings = settings

        self._stopped: Optional[asyncio.Event] = None
        self._upd_task: Optional[asyncio.Task] = None

        self._scheduler: aiojobs.Scheduler = None  # type: ignore
        self.http_client: HTTPClient = None  # type: ignore

        self.mqtt_client: Optional[MQTTClient] = None
        self.api: Optional[ApiServer] = None
        self.verifier = BACnetVerifier(override_threshold=settings.override_threshold)

        self._devices: dict[int, BasePollingDevice] = {}
        # self._cameras = dict[int, Union[SUNAPIDevice]]

        # TODO: updating event to return msg in case controlling at update time.

    @classmethod
    async def create(cls, settings: GatewaySettings) -> Gateway:
        gateway = cls(settings=settings)
        gateway._scheduler = await aiojobs.create_scheduler(close_timeout=60, limit=100)
        return gateway

    @property
    def unreachable_threshold(self) -> int:
        return self.settings.unreachable_threshold

    @property
    def unreachable_reset_period(self) -> int:
        return self.settings.unreachable_reset_period

    @property
    def poll_device_ids(self) -> list[int]:
        return self.settings.poll_device_ids

    @property
    def upd_period(self) -> int:
        return self.settings.update_period

    @property
    def _is_mqtt_enabled(self) -> bool:
        return self.settings.mqtt_enable

    def get_device(self, dev_id: int) -> Optional[BaseDevice]:
        """
        Args:
            dev_id: Device identifier.

        Returns:
            Device instance.
        """
        return self._devices.get(dev_id)

    # def run(self) -> None:
    #     # if need, set event loop policy here
    #     asyncio.run(self.async_run(), debug=True)

    async def async_run(self) -> None:
        """Gateway main entry point.
        Start Gateway and block until stopped.
        """
        # self.async_stop will set this instead of stopping the loop
        self._stopped = asyncio.Event()
        await self.async_start()

        await self._stopped.wait()

    async def async_start(self) -> None:
        await self.async_add_job(self.async_setup)

        # self.loop.run_forever()

    async def async_setup(self) -> None:
        """Set up Gateway and spawn update task."""
        self.http_client = HTTPClient(gateway=self, settings=HTTPSettings())
        if self._is_mqtt_enabled:
            self.mqtt_client = MQTTClient.create(gateway=self, settings=MQTTSettings())

        self.api = ApiServer.create(gateway=self, settings=ApiSettings())
        await self._scheduler.spawn(self.api.start())

        await self._scheduler.spawn(coro=self.periodic_update())

    async def periodic_update(self) -> None:
        """Spawn periodic update task."""
        await self._perform_start_tasks()
        await asyncio.sleep(delay=self.upd_period)
        await self._perform_stop_tasks()

        await self._scheduler.spawn(self.periodic_update())
        # self._upd_task = self.loop.create_task(self.periodic_update())

    def add_job(self, target: Callable, *args: Any) -> None:
        """Adds job to the executor pool.

        Args:
            target: target to call.
            args: parameters for target to call.
        """
        if target is None:
            raise ValueError("None not allowed")
        self.loop.call_soon_threadsafe(self.async_add_job, target, *args)

    def async_add_job(self, target: Callable, *args: Any) -> Union[Awaitable, asyncio.Task]:
        """Adds a job from within the event loop.

        Args:
            target: target to call.
            args: parameters for target to call.

        Returns:
            task or future object.
        Raises:
            Value Error if no task provided.
        """
        if target is None:
            raise ValueError("None not allowed")

        task: Union[Awaitable, asyncio.Task]
        if asyncio.iscoroutine(target) or asyncio.iscoroutinefunction(target):
            # await self._scheduler.spawn(target(*args))
            task = self.loop.create_task(target(*args))
            return task
        task = self.loop.run_in_executor(None, target, *args)
        return task

    async def async_stop(self) -> None:
        """Stops Gateway."""
        # todo wait pending tasks
        if self._stopped is not None:
            self._stopped.set()

    async def _perform_start_tasks(self) -> None:
        """Performs starting tasks.

        Setup visiobas_gateway steps:
            - Log in to HTTP
            - Load devices
            - Start devices poll
        """
        await self.http_client.wait_login()

        # Load devices.
        load_device_tasks = [
            self.load_device(dev_id=dev_id) for dev_id in self.poll_device_ids
        ]
        # await asyncio.gather(*load_device_tasks)

        for dev in asyncio.as_completed(load_device_tasks):
            dev = await dev
            if dev and isinstance(dev, BasePollingDevice):
                await dev.start_periodic_polls()

        # if self._is_mqtt_enabled:
        # TODO: subscribe

        _LOG.info(
            "Start tasks performed",
            extra={
                "gateway_settings": self.settings,
            },
        )

    async def _perform_stop_tasks(self) -> None:
        """Performs stopping tasks.

        Stop visiobas_gateway steps:
            - Unsubscribe to MQTT
            - Stop devices poll
            - Log out to HTTP
        """
        if self._is_mqtt_enabled:
            if isinstance(self.mqtt_client, MQTTClient):
                await self.mqtt_client.async_disconnect()

        # Stop polling devices.
        stop_device_polling_tasks = [
            dev.stop()
            for dev in self._devices.values()
            if dev.protocol in POLLING_PROTOCOLS
        ]
        await asyncio.gather(*stop_device_polling_tasks)
        self._devices = {}

        await self.http_client.logout()
        _LOG.info("Stop tasks performed")

    @log_exceptions
    async def load_device(self, dev_id: int) -> Optional[BaseDevice]:
        """Tries to download an object of device from server.
        Then gets polling objects and load them into device.

        When device loaded, it may be accessed by `visiobas_gateway.devices[identifier]`.

        # TODO: If fails get objects from server - loads it from local.
        """
        device_obj_data = await self.http_client.get_objects(
            dev_id=dev_id, obj_types=(ObjType.DEVICE,)
        )
        _LOG.debug("Device object downloaded", extra={"device_id": dev_id})

        if (
            not isinstance(device_obj_data, list)
            or not isinstance(device_obj_data[0], list)
            or not device_obj_data[0]
        ):
            _LOG.warning(
                "Empty device object or exception",
                extra={
                    "device_id": dev_id,
                    "data": device_obj_data,
                },
            )
            return None

        # objs in the list, so get [0] element in `dev_obj_data[0]` below
        # request one type - 'device', so [0] element of tuple below
        # todo: refactor
        device_obj = await self.async_add_job(self._parse_device_obj, device_obj_data[0][0])
        device = await self.device_factory(dev_obj=device_obj)

        if device.protocol in POLLING_PROTOCOLS:
            # todo: use for extractions tasks asyncio.as_completed(tasks):
            objs_data = await self.http_client.get_objects(
                dev_id=dev_id, obj_types=POLLING_TYPES
            )
            _LOG.debug(
                "Polling objects downloaded",
                extra={
                    "device_id": dev_id,
                },
            )

            extract_tasks = [
                self.async_add_job(self._extract_objects, obj_data, device_obj)
                for obj_data in objs_data
                if not isinstance(obj_data, (aiohttp.ClientError, Exception))
            ]
            objs_lists = await asyncio.gather(*extract_tasks)
            objs = [obj for lst in objs_lists for obj in lst if obj]  # Flat list of lists.

            if not objs:
                raise ValueError("There aren't polling objects")

            _LOG.debug(
                "Polling objects extracted",
                extra={"device_id": dev_id, "objects_count": len(objs)},
            )
            await self.async_add_job(device.insert_objects, objs)

        self._devices.update({device.device_id: device})
        _LOG.info(
            "Device loaded",
            extra={
                "device_id": dev_id,
            },
        )
        return device

    # async def start_device_poll(self, dev_id: int) -> None:
    #     """Starts poll of device."""
    #     dev = self._devices[dev_id]
    #     if dev.is_polling_device:
    #         await self.async_add_job(dev.start_periodic_polls)
    #         _LOG.info('Device polling started', extra={'device_id': dev_id})
    #     else:
    #         _LOG.warning('Is not a polling device', extra={'device_id': dev_id})

    @staticmethod
    def _parse_device_obj(dev_data: dict) -> Optional[DeviceObj]:
        """Parses and validate device object data from JSON.

        Returns:
            Parsed and validated device object, if no errors throw.
        """
        dev_obj = DeviceObj(**dev_data)
        _LOG.debug("Device object parsed", extra={"device_object": dev_obj})
        return dev_obj

    def _extract_objects(
        self, objs_data: tuple, dev_obj: DeviceObj
    ) -> list[Union[BACnetObj, ModbusObj]]:
        """Parses and validate objects data from JSON.

        Returns:
            List of parsed and validated objects.
        """
        objs = [
            self.object_factory(dev_obj=dev_obj, obj_data=obj_data)
            for obj_data in objs_data
            if not isinstance(obj_data, (aiohttp.ClientError, Exception))
        ]
        return objs

    async def verify_objects(self, objs: Collection[BACnetObj]) -> None:
        """Verify objects in executor pool."""
        await self.async_add_job(self.verifier.verify_objects, objs)

    @log_exceptions
    async def send_objects(self, objs: Collection[BACnetObj]) -> None:
        """Sends objects to server."""
        if not objs:
            raise ValueError("Cannot sent nothing")

        dev_id = list(objs)[0].device_id
        str_ = ";".join([obj.to_http_str() for obj in objs]) + ";"
        if isinstance(self.http_client, HTTPClient):
            await self.http_client.post_device(
                servers=self.http_client.servers_post, dev_id=dev_id, data=str_
            )
        # if self._is_mqtt_enabled:  # todo

    @log_exceptions
    async def device_factory(self, dev_obj: DeviceObj) -> BaseDevice:
        """Creates device for provided protocol.

        Returns:
            Created device instance.
        """
        protocol = dev_obj.property_list.protocol
        device: BaseDevice
        if protocol in {
            Protocol.MODBUS_TCP,
            Protocol.MODBUS_RTU_OVER_TCP,
            Protocol.MODBUS_RTU,
        }:
            cls = ModbusDevice  # type: ignore
            device = await cls.create(device_obj=dev_obj, gateway=self)
        elif protocol is Protocol.BACNET:
            cls = BACnetDevice  # type: ignore
            device = await cls.create(device_obj=dev_obj, gateway=self)
        elif protocol is Protocol.SUN_API:
            device = SUNAPIDevice(device_obj=dev_obj, gateway=self)
        else:
            raise NotImplementedError("Device factory not implemented")

        _LOG.debug("Device object created", extra={"device_id": device.device_id})
        return device

    @staticmethod
    @log_exceptions
    def object_factory(
        dev_obj: DeviceObj, obj_data: dict[str, Any]
    ) -> Union[ModbusObj, BACnetObj]:
        """Creates object for provided protocol data.

        Returns:
            If object created - returns created object instance.
            If object incorrect - returns None.
        """
        defaults_from_device = {
            "default_poll_period": dev_obj.property_list.poll_period,
            "default_send_period": dev_obj.property_list.send_period,
        }  # FIXME: hotfix

        protocol = dev_obj.property_list.protocol
        cls: Type[Object]
        if protocol in {
            Protocol.MODBUS_TCP,
            Protocol.MODBUS_RTU,
            Protocol.MODBUS_RTU_OVER_TCP,
        }:
            cls = ModbusObj
        elif protocol == Protocol.BACNET:
            cls = BACnetObj
        else:
            raise NotImplementedError("Not implemented protocol factory.")
        return cls(**obj_data, **defaults_from_device)
