import asyncio
from typing import Callable, Any, Optional, Union, Awaitable, Collection

import aiohttp
import aiojobs
from pydantic import ValidationError

from gateway.api import VisioGtwApi
from gateway.clients import VisioHTTPClient, VisioMQTTClient
from gateway.devices import AsyncModbusDevice, SyncModbusDevice, BACnetDevice, SUNAPIDevice
from gateway.models import (ObjType, BACnetDeviceObj, ModbusObj, Protocol,
                            BACnetObj, HTTPSettings, GatewaySettings, ApiSettings,
                            MQTTSettings)
from gateway.utils import get_file_logger
from gateway.verifier import BACnetVerifier

_LOG = get_file_logger(__name__)

# Aliases
Device = Union[
    AsyncModbusDevice, SyncModbusDevice,
    BACnetDevice,
    SUNAPIDevice
]


class VisioBASGateway:
    """VisioBAS IoT Gateway."""

    def __init__(self, settings: GatewaySettings):
        self.loop: asyncio.AbstractEventLoop = asyncio.get_running_loop()

        # self._pending_tasks: list = []
        self.settings = settings

        self._stopped: asyncio.Event = None
        self._upd_task: asyncio.Task = None

        self._scheduler: aiojobs.Scheduler = None

        self.http_client: VisioHTTPClient = None
        self.mqtt_client: VisioMQTTClient = None
        self.api: VisioGtwApi = None
        self.verifier = BACnetVerifier(override_threshold=settings.override_threshold)

        self._devices: dict[int, Device] = {}
        # self._cameras = dict[int, Union[SUNAPIDevice]]

        # TODO: updating event to return msg in case controlling at update time.

    @classmethod
    async def create(cls, settings: GatewaySettings) -> 'VisioBASGateway':
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

    def get_device(self, dev_id: int) -> Optional[Device]:
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
        self.http_client = VisioHTTPClient(gateway=self, settings=HTTPSettings())
        if self._is_mqtt_enabled:
            self.mqtt_client = VisioMQTTClient.create(gateway=self, settings=MQTTSettings())

        self.api = VisioGtwApi.create(gateway=self, settings=ApiSettings())
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
            raise ValueError('None not allowed')
        self.loop.call_soon_threadsafe(self.async_add_job, target, *args)

    def async_add_job(self, target: Callable, *args: Any
                      ) -> Optional[Union[asyncio.Future, Awaitable]]:
        """Adds a job from within the event loop.

        Args:
            target: target to call.
            args: parameters for target to call.

        Returns:
            task or future object
        """
        if target is None:
            raise ValueError('None not allowed')

        if asyncio.iscoroutine(target) or asyncio.iscoroutinefunction(target):
            # await self._scheduler.spawn(target(*args))
            task = self.loop.create_task(target(*args))
            return task
        else:
            task = self.loop.run_in_executor(None, target, *args)
            return task

    async def async_stop(self) -> None:
        """Stops Gateway."""
        # todo wait pending tasks
        if self._stopped is not None:
            self._stopped.set()

    async def _perform_start_tasks(self) -> None:
        """Performs starting tasks.

        Setup gateway steps:
            - Log in to HTTP
            - Load devices
            - Start devices poll
        """
        await self.http_client.wait_login()

        # Load devices.
        load_device_tasks = [self.load_device(dev_id=dev_id)
                             for dev_id in self.poll_device_ids]
        # await asyncio.gather(*load_device_tasks)

        for dev in asyncio.as_completed(load_device_tasks):
            dev = await dev
            if dev and dev.is_polling_device:
                await dev.start_periodic_polls()

        # # Run polling tasks.
        # start_poll_tasks = [self.start_device_poll(dev_id=dev_id)
        #                     for dev_id, dev in self._devices.items()
        #                     if dev.is_polling_device]
        # await asyncio.gather(*start_poll_tasks)

        # if self._is_mqtt_enabled:
        # TODO: subscribe

        _LOG.info('Start tasks performed',
                  extra={'gateway_settings': self.settings, })

    async def _perform_stop_tasks(self) -> None:
        """Performs stopping tasks.
        
        Stop gateway steps:
            - Unsubscribe to MQTT
            - Stop devices poll
            - Log out to HTTP
        """
        if self._is_mqtt_enabled:
            await self.mqtt_client.async_disconnect()

        # Stop polling devices.
        stop_device_polling_tasks = [dev.stop() for dev in self._devices.values()
                                     if dev.is_polling_device]
        await asyncio.gather(*stop_device_polling_tasks)
        self._devices = {}

        await self.http_client.logout()
        _LOG.info('Stop tasks performed')

    async def load_device(self, dev_id: int) -> Optional[Device]:
        """Tries to download an object of device from server.
        Then gets polling objects and load them into device.

        When device loaded, it may be accessed by `gateway.devices[identifier]`.

        # TODO: If fails get objects from server - loads it from local.
        """
        try:
            dev_obj_data = await self.http_client.get_objects(
                dev_id=dev_id, obj_types=(ObjType.DEVICE,))
            _LOG.debug('Device object downloaded', extra={'device_id': dev_id})

            if (not isinstance(dev_obj_data, list)
                    or not isinstance(dev_obj_data[0], list)
                    or not dev_obj_data[0]):
                _LOG.warning('Empty device object or exception',
                             extra={'device_id': dev_id, 'data': dev_obj_data, })
                return None

            # objs in the list, so get [0] element in `dev_obj_data[0]` below
            # request one type - 'device', so [0] element of tuple below
            dev_obj = await self.async_add_job(self._parse_device_obj, dev_obj_data[0][0])
            dev = await self.device_factory(dev_obj=dev_obj)

            if dev.is_polling_device:
                # todo: use for extractions tasks asyncio.as_completed(tasks):
                objs_data = await self.http_client.get_objects(
                    dev_id=dev_id, obj_types=dev.types_to_rq)
                _LOG.debug('Polling objects downloaded', extra={'device_id': dev_id, })

                extract_tasks = [
                    self.async_add_job(self._extract_objects, obj_data, dev_obj)
                    for obj_data in objs_data
                    if not isinstance(obj_data, (aiohttp.ClientError, Exception))
                ]
                objs_lists = await asyncio.gather(*extract_tasks)
                objs = [obj for lst in objs_lists
                        for obj in lst if obj]  # Flat list of lists.

                if not len(objs):
                    _LOG.warning("There no polling objects",
                                 extra={'device_id': dev_id})
                    return None

                _LOG.debug('Polling objects extracted',
                           extra={'device_id': dev_id, 'objects_count': len(objs)})
                await self.async_add_job(dev.insert_objects, objs)

            self._devices.update({dev.id: dev})
            _LOG.info('Device loaded', extra={'device_id': dev_id, })
            return dev
        except (ValidationError,) as e:  #
            _LOG.warning('Invalid device properties',
                         extra={'device_id': dev_id, 'exc': e, })
        except (TypeError, AttributeError, Exception) as e:
            _LOG.exception('Unhandled load device exception',
                           extra={'device_id': dev_id, 'exc': e, })

    # async def start_device_poll(self, dev_id: int) -> None:
    #     """Starts poll of device."""
    #     dev = self._devices[dev_id]
    #     if dev.is_polling_device:
    #         await self.async_add_job(dev.start_periodic_polls)
    #         _LOG.info('Device polling started', extra={'device_id': dev_id})
    #     else:
    #         _LOG.warning('Is not a polling device', extra={'device_id': dev_id})

    @staticmethod
    def _parse_device_obj(dev_data: dict) -> Optional[BACnetDeviceObj]:
        """Parses and validate device object data from JSON.

        Returns:
            Parsed and validated device object, if no errors throw.
        """
        dev_obj = BACnetDeviceObj(**dev_data)
        _LOG.debug('Device object parsed', extra={'device_object': dev_obj})
        return dev_obj

    def _extract_objects(self, objs_data: tuple, dev_obj: BACnetDeviceObj
                         ) -> list[ModbusObj]:
        """Parses and validate objects data from JSON.

        Returns:
            List of parsed and validated objects.
        """
        objs = [self.object_factory(dev_obj=dev_obj, obj_data=obj_data)
                for obj_data in objs_data
                if not None and not isinstance(obj_data, (aiohttp.ClientError, Exception))]
        return objs

    async def verify_objects(self, objs: Collection[BACnetObj]) -> None:
        """Verify objects in executor pool."""
        await self.async_add_job(self.verifier.verify_objects, objs)

    async def send_objects(self, objs: Collection[BACnetObj]) -> None:
        """Sends objects to server."""
        if not len(objs):
            # _LOG.debug('Nothing to send')
            return None

        try:
            dev_id = list(objs)[0].device_id
            str_ = ';'.join([obj.to_http_str() for obj in objs]) + ';'
            await self.http_client.post_device(servers=self.http_client.servers_post,
                                               dev_id=dev_id, data=str_)
            # if self._is_mqtt_enabled:  # todo
        except Exception as e:
            _LOG.exception('Unexpected error', extra={'exc': e})

    async def device_factory(self, dev_obj: BACnetDeviceObj) -> Optional[Device]:
        """Creates device for provided protocol.

        Returns:
            Created device instance.
        """
        try:
            protocol = dev_obj.property_list.protocol

            if protocol in {
                Protocol.MODBUS_TCP, Protocol.MODBUS_RTUOVERTCP, Protocol.MODBUS_RTU
            }:
                cls = SyncModbusDevice if self.settings.modbus_sync else AsyncModbusDevice
                device = await cls.create(device_obj=dev_obj, gateway=self)
            elif protocol is Protocol.BACNET:
                device = await BACnetDevice.create(device_obj=dev_obj, gateway=self)
            elif protocol is Protocol.SUNAPI:
                device = SUNAPIDevice(device_obj=dev_obj, gateway=self)
            else:
                raise NotImplementedError('Device factory not implemented')

            _LOG.debug('Device object created', extra={'device_id': device.id})
            return device
        except (ValidationError, AttributeError) as e:
            _LOG.warning('Failed device creation',
                         extra={'device_id': dev_obj.id, 'exc': e, })
        except Exception as e:
            _LOG.exception('Unhandled failed device creation',
                           extra={'device_id': dev_obj.id, 'exc': e, })

    @staticmethod
    def object_factory(dev_obj: BACnetDeviceObj, obj_data: dict[str, Any]
                       ) -> Optional[Union[ModbusObj, BACnetObj]]:
        """Creates object for provided protocol data.

        Returns:
            If object created - returns created object instance.
            If object incorrect - returns None.
        """
        try:

            defaults_from_device = {  # FIXME: hotfix
                'default_poll_period': dev_obj.property_list.poll_period,
                'default_send_period': dev_obj.property_list.send_period,
            }

            protocol = dev_obj.property_list.protocol
            if protocol in {Protocol.MODBUS_TCP, Protocol.MODBUS_RTU,
                            Protocol.MODBUS_RTUOVERTCP}:
                cls = ModbusObj
            elif protocol == Protocol.BACNET:
                cls = BACnetObj
            else:
                raise NotImplementedError('Not implemented protocol factory.')
            return cls(**obj_data, **defaults_from_device)
        except ValidationError as e:
            _LOG.warning('Failed polling object creation. Please check objects settings',
                         extra={'device_id': dev_obj.id,
                                'object_data': obj_data, 'exc': e, })
        except Exception as e:
            _LOG.exception('Unhandled object creation exception',
                           extra={'device_id': dev_obj.id,
                                  'object_data': obj_data, 'exc': e, })
