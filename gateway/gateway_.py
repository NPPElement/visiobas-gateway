import asyncio
from typing import Callable, Any, Optional, Union, Awaitable, Collection

import aiojobs
from pydantic import ValidationError

from gateway.clients import VisioHTTPClient, VisioBASMQTTClient
from gateway.devices import AsyncModbusDevice
from gateway.models import (ObjType, BACnetDeviceModel, ModbusObjModel, Protocol,
                            BACnetObjModel, HTTPSettings, GatewaySettings)
from gateway.utils import get_file_logger
from gateway.verifier import BACnetVerifier

_LOG = get_file_logger(__name__)


class VisioBASGateway:
    """VisioBAS IoT Gateway."""

    def __init__(self, settings: GatewaySettings):
        # self.loop = asyncio.new_event_loop()
        self.loop: asyncio.AbstractEventLoop = asyncio.get_running_loop()

        # self._pending_tasks: list = []
        self.settings = settings

        self._stopped: asyncio.Event = None
        self._upd_task: asyncio.Task = None

        self._scheduler: aiojobs.Scheduler = None

        self.http_client: VisioHTTPClient = None
        self.mqtt_client: VisioBASMQTTClient = None
        self.http_api_server = None
        self.verifier = BACnetVerifier(override_threshold=settings.override_threshold)

        self._devices: dict[int, Union[AsyncModbusDevice]] = {}

    @classmethod
    async def create(cls, settings: GatewaySettings) -> 'VisioBASGateway':
        gateway = cls(settings=settings)
        gateway._scheduler = await aiojobs.create_scheduler(close_timeout=60,
                                                            limit=100)
        return gateway

    @property
    def poll_device_ids(self) -> list[int]:
        return self.settings.poll_device_ids

    @property
    def upd_period(self) -> int:
        return self.settings.update_period

    @property
    def devices(self) -> dict[int, Union[AsyncModbusDevice]]:
        return self._devices

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
        # await self.http_client.setup()
        # self.mqtt_client = VisioBASMQTTClient.from_yaml(
        #     gateway=self, yaml_path=self.MQTT_CFG_PATH)
        # todo: setup HTTP API server
        await self._scheduler.spawn(coro=self.periodic_update())
        # self._upd_task = self.loop.create_task(self.periodic_update())

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
            - Connect to MQTT
        """
        await self.http_client.wait_login()

        # Load devices
        load_device_tasks = [self.load_device(dev_id=dev_id)
                             for dev_id in self.poll_device_ids]
        await asyncio.gather(*load_device_tasks)

        # Run polling tasks
        start_poll_tasks = [self.start_device_poll(dev_id=dev_id)
                            for dev_id in self._devices.keys()]
        await asyncio.gather(*start_poll_tasks)
        # todo await self.mqtt_client.subscribe(self.mqtt_client.topics)
        _LOG.info('Start tasks performed')

    async def _perform_stop_tasks(self) -> None:
        """Performs stopping tasks.

        Stop gateway steps:
            - Unsubscribe to MQTT
            - Stop devices poll
            - Log out to HTTP
        """
        # todo await self.mqtt_client.unsubscribe(self.mqtt_client.topics)
        stop_device_tasks = [dev.stop for dev in self.devices.values()]
        await asyncio.gather(*stop_device_tasks)
        self._devices = {}

        await self.http_client.logout()
        _LOG.info('Stop tasks performed')

    async def load_device(self, dev_id: int) -> None:
        """Tries to download an object of device from server.
        Then gets polling objects and load them into device.

        When device loaded, it may be accessed by `gateway.devices[identifier]`.

        If fails get objects from server - loads it from local.
        """
        try:
            dev_obj_data = await self.http_client.get_objs(dev_id=dev_id,
                                                           obj_types=(ObjType.DEVICE,))
            _LOG.debug('Device object downloaded', extra={'device_id': dev_id})

            if not dev_obj_data:
                _LOG.warning('Empty device object', extra={'device_id': dev_id})
                return None

            # objs in the list, so get [0] element in `dev_obj_data[0]` below
            dev_obj = await self.async_add_job(self._parse_device_obj, dev_obj_data[0])

            device = await self.device_factory(dev_obj=dev_obj)

            # fixme use for task in asyncio.as_completed(tasks):
            objs_data = await self.http_client.get_objs(dev_id=dev_id,
                                                        obj_types=device.types_to_rq)
            _LOG.debug('Polling objects downloaded', extra={'device_id': dev_id})

            extract_tasks = [self.async_add_job(self._extract_objects, obj_data, dev_obj)
                             for obj_data in objs_data]
            objs_lists = await asyncio.gather(*extract_tasks)
            objs = [obj for lst in objs_lists for obj in lst]  # flat list of lists

            if not len(objs):  # if there are objects
                _LOG.warning("There aren't polling objects", extra={'device_id': dev_id})
                return None

            _LOG.debug('Polling objects extracted',
                       extra={'device_id': dev_id, 'objects_count': len(objs)})
            await self.async_add_job(device.load_objects, objs)

            self._devices.update({device.id: device})
            _LOG.info('Device loaded', extra={'device_id': dev_id})
        except (ValidationError, AttributeError) as e:
            _LOG.warning('Cannot load device',
                         extra={'device_id': dev_id, 'exc': e, })
        except Exception as e:
            _LOG.exception('Unhandled load device exception',
                           extra={'device_id': dev_id, 'exc': e, })

    async def start_device_poll(self, dev_id: int) -> None:
        """Starts poll of device."""
        await self.async_add_job(self.devices[dev_id].start_periodic_polls)
        _LOG.info('Device polling started', extra={'device_id': dev_id})

    @staticmethod
    def _parse_device_obj(dev_data: dict) -> Optional[BACnetDeviceModel]:
        """Parses and validate device object data from JSON.

        Returns:
            Parsed and validated device object, if no errors throw.
        """
        dev_obj = BACnetDeviceModel(**dev_data)
        _LOG.debug('Device object parsed', extra={'device_object': dev_obj})
        return dev_obj

    def _extract_objects(self, objs_data: tuple, dev_obj: BACnetDeviceModel
                         ) -> list[ModbusObjModel]:
        """Parses and validate objects data from JSON.

        Returns:
            List of parsed and validated objects.
        """
        objs = [self.object_factory(dev_obj=dev_obj, obj_data=obj_data)
                for obj_data in objs_data
                if not None]
        return objs

    async def verify_objects(self, objs: Collection[BACnetObjModel]) -> None:
        """Verify objects in executor pool."""
        await self.async_add_job(self.verifier.verify_objects, objs)

    async def send_objects(self, objs: Collection[BACnetObjModel]) -> None:
        """Sends objects to server."""
        assert len(objs)

        dev_id = list(objs)[0].device_id

        str_ = ';'.join([obj.to_http_str() for obj in objs]) + ';'
        await self.http_client.post_device(servers=self.http_client.servers_post,
                                           dev_id=dev_id,
                                           data=str_)

    async def device_factory(self, dev_obj: BACnetDeviceModel
                             ) -> Optional[Union[AsyncModbusDevice]]:
        """Creates device for provided protocol.

        Returns:
            Created device.
        """
        try:
            protocol = dev_obj.property_list.protocol
            if protocol in {Protocol.MODBUS_TCP, Protocol.MODBUS_RTU,
                            Protocol.MODBUS_RTUOVERTCP}:
                device = await AsyncModbusDevice.create(device_obj=dev_obj, gateway=self)
            elif protocol == Protocol.BACNET:
                device = None  # todo
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
    def object_factory(dev_obj: BACnetDeviceModel, obj_data: dict[str, Any]
                       ) -> Optional[Union[ModbusObjModel, BACnetObjModel]]:
        """Creates object for provided protocol data.

        Returns:
            If object created - returns created object.
            If object incorrect - returns None.
        """
        try:
            protocol = dev_obj.property_list.protocol
            if protocol in {Protocol.MODBUS_TCP, Protocol.MODBUS_RTU}:
                obj = ModbusObjModel(**obj_data)  # todo switch to parse_raw
            elif protocol == Protocol.BACNET:
                obj = None  # todo
            else:
                # unknown protocols logging by `pydantic` on enter
                raise NotImplementedError('Not implemented protocol factory.')
            return obj
        except ValidationError as e:
            _LOG.warning('Failed polling object creation',
                         extra={'device_id': dev_obj.id,
                                'object_data': obj_data, 'exc': e, })
        except Exception as e:
            _LOG.exception('Unhandled object creation exception',
                           extra={'device_id': dev_obj.id,
                                  'object_data': obj_data, 'exc': e, })
