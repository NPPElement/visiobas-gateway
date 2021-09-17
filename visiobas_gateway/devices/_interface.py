import asyncio
from dataclasses import dataclass
from typing import Any


@dataclass
class Interface:
    """Interface for interaction with controller."""

    name: str  # Interface name.
    used_by: set[int]  # Set of device_ids.

    client: Any  # Client to interact with controllers.
    client_connected: bool  # Is client connected.

    lock: asyncio.Lock  # Lock to interact with clients.
    polling_event: asyncio.Event  # Event to block read when write should happen.
