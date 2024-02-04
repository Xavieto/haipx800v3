"""Support for IPX800 V3 switches."""
import logging
from typing import Any

from pyipx800v3_async import IPX800V3, Ipx800v3CannotConnectError, Ipx800v3InvalidAuthError, Ipx800v3RequestError, Output

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from . import IpxEntity
from .const import (
    CONF_DEVICES,
    CONF_TYPE,
    CONTROLLER,
    COORDINATOR,
    DOMAIN,
    GLOBAL_PARALLEL_UPDATES,
    TYPE_RELAY
)

_LOGGER = logging.getLogger(__name__)
PARALLEL_UPDATES = GLOBAL_PARALLEL_UPDATES


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the IPX800 switches."""
    controller = hass.data[DOMAIN][entry.entry_id][CONTROLLER]
    coordinator = hass.data[DOMAIN][entry.entry_id][COORDINATOR]
    devices = hass.data[DOMAIN][entry.entry_id][CONF_DEVICES]["switch"]

    entities: list[SwitchEntity] = []

    for device in devices:
        if device.get(CONF_TYPE) == TYPE_RELAY:
            entities.append(RelaySwitch(device, controller, coordinator))

    async_add_entities(entities, True)


class RelaySwitch(IpxEntity, SwitchEntity):
    """Representation of a IPX Switch through relay."""

    def __init__(
        self,
        device_config: dict,
        ipx: IPX800V3,
        coordinator: DataUpdateCoordinator,
    ) -> None:
        """Initialize the RelaySwitch."""
        super().__init__(device_config, ipx, coordinator)
        self.control = Output(ipx, self._id)

    @property
    def is_on(self) -> bool:
        """Return the state."""
        return self.coordinator.data[f"OUT{self._id}"] == 1

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn on the switch."""
        try:
            await self.control.on()
            await self.coordinator.async_request_refresh()
        except (Ipx800v3CannotConnectError, Ipx800v3InvalidAuthError, Ipx800v3RequestError):
            _LOGGER.error("An error occurred while turn on IPX800 switch: %s", self.name)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off the switch."""
        try:
            await self.control.off()
            await self.coordinator.async_request_refresh()
        except (Ipx800v3CannotConnectError, Ipx800v3InvalidAuthError, Ipx800v3RequestError):
            _LOGGER.error(
                "An error occurred while turn off IPX800 switch: %s", self.name
            )

    async def async_toggle(self, **kwargs: Any) -> None:
        """Toggle the switch."""
        try:
            await self.control.toggle()
            await self.coordinator.async_request_refresh()
        except (Ipx800v3CannotConnectError, Ipx800v3InvalidAuthError, Ipx800v3RequestError):
            _LOGGER.error("An error occurred while toggle IPX800 switch: %s", self.name)

