from __future__ import annotations

from typing import TYPE_CHECKING

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
        self._scheduler: aiojobs.Scheduler = None # type: ignore

    def __repr__(self) -> str:
        return f'{self.__class__.__name__}({self._settings})'

    @classmethod
    async def create(cls, gateway: Gateway, settings: BaseSettings) -> AbstractBaseClient:
        """Client factory. Use it to create the client."""
        client = cls(gateway=gateway, settings=settings)
        client._scheduler = await aiojobs.create_scheduler(close_timeout=60, limit=None)
        return client

    @abstractmethod
    async def _startup_tasks(self):
        """ """

    @abstractmethod
    async def _shutdown_tasks(self):
        """ """

    @abstractmethod
    async def start(self) -> None:
        """ """



