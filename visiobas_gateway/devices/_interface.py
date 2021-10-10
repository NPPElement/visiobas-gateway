from __future__ import annotations

import asyncio
from dataclasses import dataclass
from ipaddress import IPv4Address
from typing import Any

from ..schemas.serial_port import SerialPort


@dataclass
class Interface:
    """Interface for interaction with controller."""

    interface_key: tuple[IPv4Address, int] | SerialPort
    used_by: set[int]  # Set of device_ids.

    client: Any  # Client to interact with controllers.
    client_connected: bool  # Is client connected.

    lock: asyncio.Lock  # Lock to interact with clients.
    polling_event: asyncio.Event  # Event to block read when write should happen.

    # IMPORTANT: `clear()` that event to change the objects (load or priority write).
    # `wait()` that event in polling to provide priority access to write_with_check.
