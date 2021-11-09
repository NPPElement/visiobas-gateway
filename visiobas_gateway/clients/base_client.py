from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, Iterable

import aiojobs  # type: ignore
from pydantic import BaseSettings

from ..schemas import BACnetObj
from ..schemas.send_methods import SendMethod
from ..utils import get_file_logger

if TYPE_CHECKING:
    from ..gateway import Gateway
else:
    Gateway = "Gateway"

_LOG = get_file_logger(name=__name__)


class AbstractBaseClient(ABC):
    """Base class for gateway's clients."""

    def __init__(self, gateway: Gateway, settings: Any | BaseSettings):
        self._gtw = gateway
        self._settings: Any = settings
        self._scheduler: aiojobs.Scheduler = None  # type: ignore

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self._settings})"

    @abstractmethod
    def get_send_method(self) -> SendMethod:
        """Returns SendMethod key used to identify client."""

    @classmethod
    async def create(cls, gateway: Gateway, settings: Any) -> AbstractBaseClient:
        """Client factory. Use it to create the client."""
        _LOG.debug("Creating client", extra={"client": cls.__name__})
        client = cls(gateway=gateway, settings=settings)
        await client.async_init_client(settings=settings)
        _LOG.info("Client created", extra={"client": cls.__name__, "settings": settings})
        return client

    @abstractmethod
    async def async_init_client(self, settings: Any) -> None:
        """If client initialization requires async operations -
        they should be called here.
        """

    @abstractmethod
    async def _startup_tasks(self) -> None:
        """ """

    @abstractmethod
    async def _shutdown_tasks(self) -> None:
        """ """

    @abstractmethod
    def objects_to_message(self, objs: Iterable[BACnetObj]) -> str:
        """Formats objects to message for sending.

        Filters objects by `send_method`.
        """

    @abstractmethod
    async def send_objects(self, objs: Iterable[BACnetObj]) -> None:
        """Sends objects to the server."""

    async def start(self) -> None:
        """Starts the client."""
        _LOG.debug("Starting client", extra={"client": self.__class__.__name__})
        self._scheduler = await aiojobs.create_scheduler(close_timeout=5, limit=None)
        await self._startup_tasks()
        _LOG.info(
            "Client started",
            extra={"client": self.__class__.__name__, "settings": repr(self._settings)},
        )

    async def stop(self) -> None:
        """Stops the client."""
        _LOG.debug("Stopping client", extra={"client": self.__class__.__name__})
        await self._shutdown_tasks()
        await self._scheduler.close()
        _LOG.info("Client stopped", extra={"client": self.__class__.__name__})
