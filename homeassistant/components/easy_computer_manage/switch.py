# Some code is from the official wake_on_lan integration

from __future__ import annotations

import logging
import subprocess as sp
from typing import Any

import voluptuous as vol
import wakeonlan

from homeassistant.components.switch import (
    PLATFORM_SCHEMA as PARENT_PLATFORM_SCHEMA,
    SwitchEntity,
)
from homeassistant.const import (
    CONF_BROADCAST_ADDRESS,
    CONF_BROADCAST_PORT,
    CONF_HOST,
    CONF_MAC,
    CONF_NAME,
    CONF_PASSWORD,
    CONF_PORT,
    CONF_USERNAME,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers import (
    config_validation as cv,
    device_registry as dr,
    entity_platform,
)
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.script import Script
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType

from . import utils
from ...config_entries import ConfigEntry
from .const import DOMAIN, SERVICE_RESTART_TO_WINDOWS_FROM_LINUX

_LOGGER = logging.getLogger(__name__)

CONF_OFF_ACTION = "turn_off"

DEFAULT_NAME = "Computer Management (WoL, SoL)"
DEFAULT_PING_TIMEOUT = 1

PLATFORM_SCHEMA = PARENT_PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_MAC): cv.string,
        vol.Optional(CONF_BROADCAST_ADDRESS): cv.string,
        vol.Optional(CONF_BROADCAST_PORT): cv.port,
        vol.Required(CONF_HOST): cv.string,
        vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
        vol.Optional(CONF_OFF_ACTION): cv.SCRIPT_SCHEMA,
        vol.Required(CONF_USERNAME, default="root"): cv.string,
        vol.Required(CONF_PASSWORD, default="root"): cv.string,
        vol.Optional(CONF_PORT, default=22): cv.string,
    }
)


def setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Set up a computer switch."""
    broadcast_address: str | None = config.get(CONF_BROADCAST_ADDRESS)
    broadcast_port: int | None = config.get(CONF_BROADCAST_PORT)
    host: str | None = config.get(CONF_HOST)
    mac_address: str = config[CONF_MAC]
    name: str = config[CONF_NAME]
    off_action: list[Any] | None = config.get(CONF_OFF_ACTION)
    username: str = config[CONF_USERNAME]
    password: str = config[CONF_PASSWORD]
    port: int = config[CONF_PORT]

    add_entities(
        [
            ComputerSwitch(
                hass,
                name,
                host,
                mac_address,
                off_action,
                broadcast_address,
                broadcast_port,
                username,
                password,
                port,
            ),
        ],
        host is not None,
    )


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> None:
    platform = entity_platform.async_get_current_platform()
    platform.async_register_entity_service(
        SERVICE_RESTART_TO_WINDOWS_FROM_LINUX,
        {vol.Required("test"): cv.boolean},
        "restart_to_windows_from_linux",
    )


class ComputerSwitch(SwitchEntity):
    """Representation of a computer switch."""

    def __init__(
        self,
        hass: HomeAssistant,
        name: str,
        host: str | None,
        mac_address: str,
        off_action: list[Any] | None,
        broadcast_address: str | None,
        broadcast_port: int | None,
        username: str,
        password: str,
        port: int | None,
    ) -> None:
        """Initialize the WOL switch."""
        self._attr_name = name
        self._host = host
        self._mac_address = mac_address
        self._broadcast_address = broadcast_address
        self._broadcast_port = broadcast_port
        self._username = username
        self._password = password
        self._port = port
        self._off_script = (
            Script(hass, off_action, name, DOMAIN) if off_action else None
        )
        self._state = False
        self._attr_assumed_state = host is None
        self._attr_should_poll = bool(not self._attr_assumed_state)
        self._attr_unique_id = dr.format_mac(mac_address)
        self._attr_extra_state_attributes = {}

        self._connection = utils.create_ssh_connection(
            self._host, self._username, self._password
        )

    @property
    def is_on(self) -> bool:
        """Return true if switch is on."""
        return self._state

    def turn_on(self, **kwargs: Any) -> None:
        """Turn the device on."""
        service_kwargs: dict[str, Any] = {}
        if self._broadcast_address is not None:
            service_kwargs["ip_address"] = self._broadcast_address
        if self._broadcast_port is not None:
            service_kwargs["port"] = self._broadcast_port

        _LOGGER.info(
            "Send magic packet to mac %s (broadcast: %s, port: %s)",
            self._mac_address,
            self._broadcast_address,
            self._broadcast_port,
        )

        wakeonlan.send_magic_packet(self._mac_address, **service_kwargs)

        if self._attr_assumed_state:
            self._state = True
            self.async_write_ha_state()

    def turn_off(self, **kwargs: Any) -> None:
        utils.sleep_system(self._connection)

        if self._attr_assumed_state:
            self._state = False
            self.async_write_ha_state()

    def restart_to_windows_from_linux(self) -> None:
        utils.restart_to_windows_from_linux(self._connection)

    def update(self) -> None:
        """Check if device is on and update the state. Only called if assumed state is false."""
        ping_cmd = [
            "ping",
            "-c",
            "1",
            "-W",
            str(DEFAULT_PING_TIMEOUT),
            str(self._host),
        ]
        status = sp.call(ping_cmd, stdout=sp.DEVNULL, stderr=sp.DEVNULL)
        self._state = not bool(status)

        self._attr_extra_state_attributes = {
            "operating_system": utils.get_operating_system(self._connection),
            "operating_system_version": utils.get_operating_system_version(
                self._connection
            ),
        }
