from __future__ import annotations

import asyncio
from typing import (
    TYPE_CHECKING,
    Any,
    Awaitable,
    Callable,
    Collection,
    Iterable,
    Type,
    Union,
)

import aiohttp
import aiojobs  # type: ignore
from pydantic import BaseSettings

from visiobas_gateway.api import ApiServer
from visiobas_gateway.clients import HttpClient, MqttClient
from visiobas_gateway.clients.base_client import AbstractBaseClient
from visiobas_gateway.devices import BACnetDevice, ModbusDevice
from visiobas_gateway.devices.base_polling_device import AbstractBasePollingDevice
from visiobas_gateway.schemas import BACnetObj, DeviceObj, ObjType
from visiobas_gateway.schemas.bacnet.device_obj import POLLING_TYPES
from visiobas_gateway.schemas.bacnet.obj import group_by_period
from visiobas_gateway.schemas.modbus.obj import ModbusObj
from visiobas_gateway.schemas.protocol import POLLING_PROTOCOLS, Protocol
from visiobas_gateway.schemas.send_methods import SendMethod
from visiobas_gateway.schemas.settings import (
    ApiSettings,
    GatewaySettings,
    HttpSettings,
    MqttSettings,
)
from visiobas_gateway.utils import get_file_logger, log_exceptions
from visiobas_gateway.verifier import BACnetVerifier

if TYPE_CHECKING:
    from .devices.base_device import BaseDevice
else:
    BaseDevice = "BaseDevice"

_LOG = get_file_logger(name=__name__)

Object = Union[BACnetObj, ModbusObj]
ObjectType = Type[Object]


class Gateway:
    """VisioBAS Gateway."""

    # pylint:disable=too-many-instance-attributes

    def __init__(
            self,
            gateway_settings: GatewaySettings,
            clients_settings: Iterable[BaseSettings],
            api_settings: ApiSettings,
    ):
        """Note: `Gateway.create()` must be used for gateway Instance construction."""
        self.loop: asyncio.AbstractEventLoop = asyncio.get_running_loop()

        self._stopped: asyncio.Event | None = None
        # todo: self.state
        # TODO: updating event to return msg in case controlling at update time.

        self._scheduler: aiojobs.Scheduler = None  # type: ignore

        self.settings = gateway_settings
        self._clients_settings = clients_settings
        self._api_settings = api_settings

        self.clients: dict[SendMethod, AbstractBaseClient] = {}
        self.api: ApiServer | None = None
        self.verifier = BACnetVerifier(
            override_threshold=gateway_settings.override_threshold
        )
        self.devices: dict[int, Any] = {}

    @classmethod
    async def create(
            cls,
            gateway_settings: GatewaySettings,
            clients_settings: Iterable[BaseSettings],
            api_settings: ApiSettings,
    ) -> Gateway:
        """Creates `Gateway`.

        Accepts same args as `Gateway`.
        """
        gateway = cls(
            gateway_settings=gateway_settings,
            clients_settings=clients_settings,
            api_settings=api_settings,
        )
        gateway._scheduler = await aiojobs.create_scheduler(close_timeout=60, limit=None)
        await gateway._create_clients(settings=clients_settings)
        await gateway._start_clients()
        return gateway

    async def _create_clients(self, settings: Iterable[BaseSettings]) -> None:
        """Creates clients for gateway."""
        tasks = []
        for client_settings in settings:
            try:
                client_cls: Any
                if isinstance(client_settings, HttpSettings):
                    client_cls = HttpClient
                elif isinstance(client_settings, MqttSettings):
                    continue  # todo: fix MQTT client
                    # client_cls = MqttClient
                else:
                    raise ValueError(
                        f"Client for {type(client_settings)} not implemented yet"
                    )
                tasks.append(client_cls.create(gateway=self, settings=client_settings))
            except Exception as exc:  # pylint:disable=broad-except
                _LOG.warning(
                    "Cannot create client",
                    extra={
                        "settings_type": type(client_settings),
                        "settings": client_settings,
                        "exception": exc,
                    },
                )
        clients = await asyncio.gather(*tasks)
        for client in clients:
            if isinstance(client, AbstractBaseClient):
                self.clients[client.get_send_method()] = client

    async def _start_clients(self) -> None:
        tasks = [client.start() for client in self.clients.values()]
        await asyncio.gather(*tasks)

    async def _stop_clients(self) -> None:
        tasks = [client.stop() for client in self.clients.values()]
        await asyncio.gather(*tasks)

    def get_device(self, dev_id: int) -> BaseDevice | None:
        """
        Args:
            dev_id: Device identifier.

        Returns:
            Device instance.
        """
        return self.devices.get(dev_id)

    # def run(self) -> None:
    #     # if need, set event loop policy here
    #     asyncio.run(self.async_run(), debug=True)

    async def run(self) -> None:
        """Gateway main entry point.
        Start Gateway and block until stopped.
        """
        # self.async_stop will set this instead of stopping the loop
        self._stopped = asyncio.Event()
        await self.start()
        await self._stopped.wait()
        await self._shutdown_tasks()

    async def stop(self) -> None:
        """Stops Gateway and closes scheduler."""
        if self._stopped is not None:
            self._stopped.set()
        await self._scheduler.close()
        await self._stop_clients()

    async def start(self) -> None:
        await self._scheduler.spawn(self.async_setup())

    async def async_setup(self) -> None:
        """Sets up gateway and spawn update task."""
        # gateway = await gateway._create_clients(  # pylint: disable=protected-access
        #     gateway=gateway, http_settings=http_settings, mqtt_settings=mqtt_settings
        # )
        self.api = await ApiServer.create(gateway=self, settings=self._api_settings)
        await self._scheduler.spawn(self.api.start())
        await self._scheduler.spawn(self.periodic_update(settings=self.settings))

    async def periodic_update(self, settings: GatewaySettings) -> None:
        """Spawn periodic update task."""
        await self._startup_tasks(settings=settings)
        await asyncio.sleep(delay=settings.update_period)
        await self._shutdown_tasks()
        await self._scheduler.spawn(self.periodic_update(settings=settings))

    # def add_job(self, target: Callable, *args: Any) -> None:
    #     """Adds job to the executor pool.
    #
    #     Args:
    #         target: target to call.
    #         args: parameters for target to call.
    #     """
    #     if target is None:
    #         raise ValueError("`None` not allowed")
    #     self.loop.call_soon_threadsafe(self.async_add_job, target, *args)

    def async_add_job(self, target: Callable, *args: Any) -> Awaitable | asyncio.Task:
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

        task: Awaitable | asyncio.Task
        if asyncio.iscoroutine(target) or asyncio.iscoroutinefunction(target):
            # await self._scheduler.spawn(target(*args))
            task = self.loop.create_task(target(*args))
            return task
        task = self.loop.run_in_executor(None, target, *args)
        return task

    @log_exceptions(logger=_LOG)
    async def _startup_tasks(self, settings: GatewaySettings) -> None:
        """Performs starting tasks."""

        # 0. Create clients. OUTDATED: will be removed soon

        # 1. Load devices tasks.
        load_device_tasks = [
            self.download_device(device_id=dev_id) for dev_id in settings.poll_device_ids
        ]

        # 2. Start devices polling.
        for ready_device in asyncio.as_completed(load_device_tasks, timeout=60):
            try:
                ready_device = await ready_device
            except (OSError, Exception) as e:  # pylint: disable=broad-except
                ready_device = e  # type: ignore
            if isinstance(ready_device, AbstractBasePollingDevice):
                await self._scheduler.spawn(  # pylint: disable=protected-access
                    ready_device.start_periodic_polls()
                )
            else:
                _LOG.warning(
                    "Device not started. Expected device type `BasePollingDevice`",
                    extra={"device": ready_device, "device_type": type(ready_device)},
                )
        _LOG.info("Start tasks performed", extra={"gateway_settings": settings})

    async def _stop_devices(self, device_ids: Iterable[int]) -> None:
        """Shutdowns devices for gateway."""
        stop_device_polling_tasks = [
            device.stop()
            for device_id, device in self.devices.items()
            if device.protocol in POLLING_PROTOCOLS and device_id in device_ids
        ]
        await asyncio.gather(*stop_device_polling_tasks)

    async def _shutdown_tasks(self) -> None:
        """Performs stopping tasks for `gateway`."""

        # 0. Stop devices polling.
        await self._stop_devices(device_ids=self.devices.keys())

        # 1. todo: save devices config to local

        # 2. Shutdown clients. OUTDATED: will be removed soon
        # gateway = await self._shutdown_clients()

        _LOG.info("Shutdown tasks performed")

    @log_exceptions(logger=_LOG)
    async def download_device(self, device_id: int) -> BaseDevice | None:
        """Tries to download an object of device from server.
        Then gets polling objects and load them into device.

        When device loaded, it may be accessed by `gateway.devices[identifier]`.

        # TODO: If fails get objects from server - loads it from local.
        """
        http_client = self.clients.get(SendMethod.HTTP)

        if not isinstance(http_client, HttpClient):
            raise NotImplementedError

        device_obj_data = await http_client.get_objects(
            dev_id=device_id, obj_types=(ObjType.DEVICE,)
        )
        _LOG.debug("Device object downloaded", extra={"device_id": device_id})

        # todo: refactor
        if (
                not isinstance(device_obj_data, list)
                or not isinstance(device_obj_data[0], list)
                or not device_obj_data[0]
        ):
            _LOG.warning(
                "Empty device object or exception",
                extra={"device_id": device_id, "data": device_obj_data},
            )
            raise ValueError("Device data not loaded.")

        # objs in the list, so get [0] element in `dev_obj_data[0]` below
        # request one type - 'device', so [0] element of tuple below
        # todo: refactor
        device_obj = self._parse_device_obj(data=device_obj_data[0][0])
        device = await self.device_factory(dev_obj=device_obj, gateway=self)

        if not device:
            raise ValueError("Device not constructed")

        if device.protocol in POLLING_PROTOCOLS:
            groups = await self.download_objects(device_obj=device_obj)
            device.object_groups = groups

        self.devices.update({device.id: device})
        _LOG.info("Device loaded", extra={"device": device})
        return device

    async def download_objects(
            self, device_obj: DeviceObj
    ) -> dict[float, dict[tuple[int, int], BACnetObj]]:

        http_client = self.clients.get(SendMethod.HTTP)

        # todo: use for extractions tasks asyncio.as_completed(tasks):
        if not isinstance(http_client, HttpClient):
            raise NotImplementedError

        objs_data = await http_client.get_objects(
            dev_id=device_obj.object_id, obj_types=POLLING_TYPES
        )
        _LOG.debug("Polling objects downloaded", extra={"device_id": device_obj.object_id})

        # todo: refactor!
        extract_tasks = [
            self.async_add_job(self._extract_objects, obj_data, device_obj)
            for obj_data in objs_data
            if not isinstance(obj_data, (aiohttp.ClientError, Exception))
        ]
        objs_lists = await asyncio.gather(*extract_tasks)
        objs = [obj for lst in objs_lists for obj in lst if obj]  # Flat list of lists.
        _LOG.debug(
            "Polling objects created",
            extra={"device_id": device_obj.object_id, "objects_count": len(objs)},
        )

        if not objs:
            raise ValueError("Polling objects not loaded")

        groups = group_by_period(objs=objs)
        return groups

    @staticmethod
    def _parse_device_obj(data: dict) -> DeviceObj | None:
        """Parses and validate device object data from JSON.

        Returns:
            Parsed and validated device object, if no errors throw.
        """
        dev_obj = DeviceObj(**data)
        _LOG.debug("Device object parsed", extra={"device_object": dev_obj})
        return dev_obj

    def _extract_objects(
            self, data: tuple, dev_obj: DeviceObj
    ) -> list[BACnetObj | ModbusObj]:
        """Parses and validate objects data from JSON.

        Returns:
            List of parsed and validated objects.

        # todo: use pydantic for parsing
        """
        objs = [
            self.object_factory(dev_obj=dev_obj, obj_data=obj_data)
            for obj_data in data
            if not isinstance(obj_data, (aiohttp.ClientError, Exception))
        ]
        return objs

    @log_exceptions(logger=_LOG, parameters_enabled=False)
    async def send_objects(self, objs: Collection[BACnetObj]) -> None:
        """Sends objects to server."""
        if not objs:
            return None
        tasks = [client.send_objects(objs=objs) for client in self.clients.values()]
        await asyncio.gather(*tasks)

    @staticmethod
    @log_exceptions(_LOG)
    async def device_factory(gateway: Gateway, dev_obj: DeviceObj) -> BaseDevice:
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
        elif protocol is Protocol.BACNET:
            cls = BACnetDevice  # type: ignore
        # elif protocol is Protocol.SUN_API:
        #     cls = SUNAPIDevice(device_obj=dev_obj, gateway=self)
        else:
            raise NotImplementedError("Device factory not implemented")

        device = await cls.create(device_obj=dev_obj, gateway=gateway)

        _LOG.debug("Device object created", extra={"device": device})
        return device

    @staticmethod
    @log_exceptions(logger=_LOG)
    def object_factory(
            dev_obj: DeviceObj, obj_data: dict[str, Any]
    ) -> ModbusObj | BACnetObj:
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
        cls: ObjectType
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
