from __future__ import annotations

from typing import TYPE_CHECKING, Any

import aiojobs
from pydantic import BaseSettings
from abc import ABC, abstractmethod
from utils import get_file_logger

if TYPE_CHECKING:
    from ..gateway import Gateway
else:
    Gateway = "Gateway"

_LOG = get_file_logger(name=__name__)


class AbstractBaseClient(ABC):

    def __init__(self, gateway: Gateway, settings: BaseSettings):
        self._gtw = gateway
        self._settings = settings
        self._client: Any = None
        self._scheduler: aiojobs.Scheduler = None  # type: ignore

    def __repr__(self) -> str:
        return f'{self.__class__.__name__}({self._settings})'

    @classmethod
    async def create(cls, gateway: Gateway, settings: BaseSettings) -> AbstractBaseClient:
        """Client factory. Use it to create the client."""
        client = cls(gateway=gateway, settings=settings)
        await client.init_client(settings=settings)
        _LOG.info('Client created', extra={'client': cls.__name__, 'settings': settings})
        return client

    @abstractmethod
    async def init_client(self, settings: BaseSettings) -> None:
        """Initializes required client."""

    @abstractmethod
    async def _startup_tasks(self) -> None:
        """ """

    @abstractmethod
    async def _shutdown_tasks(self) -> None:
        """ """

    async def start(self) -> None:
        """ """
        _LOG.debug('Starting client', extra={'client': self.__class__.__name__})
        self._scheduler = await aiojobs.create_scheduler(close_timeout=5, limit=None)
        await self._startup_tasks()
        _LOG.info('Client started', extra={'client': self.__class__.__name__, 'settings':
            repr(self._settings)})

    async def stop(self) -> None:
        """ """
        _LOG.debug('Stopping client', extra={'client': self.__class__.__name__})
        await self._shutdown_tasks()
        await self._scheduler.close()
        _LOG.info('Client stopped', extra={'client': self.__class__.__name__})
