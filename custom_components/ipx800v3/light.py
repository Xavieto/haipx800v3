"""Support for IPX800 V4 lights."""
from asyncio import gather as async_gather
import logging
from typing import Any

from pyipx800v3_async import IPX800V3, Ipx800v3CannotConnectError, Ipx800v3InvalidAuthError, Ipx800v3RequestError, Output

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_RGB_COLOR,
    ATTR_RGBW_COLOR,
    ATTR_TRANSITION,
    ColorMode,
    LightEntity,
    LightEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from . import IpxEntity
from .const import (
    CONF_DEFAULT_BRIGHTNESS,
    CONF_DEVICES,
    CONF_TRANSITION,
    CONF_TYPE,
    CONTROLLER,
    COORDINATOR,
    DEFAULT_TRANSITION,
    DOMAIN,
    GLOBAL_PARALLEL_UPDATES,
    TYPE_RELAY
)

_LOGGER = logging.getLogger(__name__)
PARALLEL_UPDATES = GLOBAL_PARALLEL_UPDATES


def scaleto255(value):
    """Scale to Home-Assistant value."""
    return max(0, min(255, round((value * 255.0) / 100.0)))


def scaleto100(value):
    """Scale to IPX800 value."""
    return max(0, min(100, round((value * 100.0) / 255.0)))


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the IPX800V3 lights."""
    controller = hass.data[DOMAIN][entry.entry_id][CONTROLLER]
    coordinator = hass.data[DOMAIN][entry.entry_id][COORDINATOR]
    devices = hass.data[DOMAIN][entry.entry_id][CONF_DEVICES]["light"]

    entities: list[LightEntity] = []

    for device in devices:
        if device.get(CONF_TYPE) == TYPE_RELAY:
            entities.append(RelayLight(device, controller, coordinator))

    async_add_entities(entities, True)


class RelayLight(IpxEntity, LightEntity):
    """Representation of a IPX Light through relay."""

    def __init__(
        self,
        device_config: dict,
        ipx: IPX800V3,
        coordinator: DataUpdateCoordinator,
    ) -> None:
        """Initialize the RelayLight."""
        super().__init__(device_config, ipx, coordinator)
        self.control = Output(ipx, self._id)
        self._attr_supported_color_modes = {ColorMode.ONOFF}
        self._attr_color_mode = ColorMode.ONOFF

    @property
    def is_on(self) -> bool:
        """Return if the light is on."""
        return self.coordinator.data[f"OUT{self._id}"] == 1

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn on the light."""
        try:
            await self.control.on()
            await self.coordinator.async_request_refresh()
        except (Ipx800v3CannotConnectError, Ipx800v3InvalidAuthError, Ipx800v3RequestError):
            _LOGGER.error(
                "An error occurred while turning on IPX800 light: %s", self.name
            )
            return None

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off the light."""
        try:
            await self.control.off()
            await self.coordinator.async_request_refresh()
        except (Ipx800v3CannotConnectError, Ipx800v3InvalidAuthError, Ipx800v3RequestError):
            _LOGGER.error(
                "An error occurred while turning off IPX800 light: %s", self.name
            )
            return None

    async def async_toggle(self, **kwargs: Any) -> None:
        """Toggle the light."""
        try:
            await self.control.toggle()
            await self.coordinator.async_request_refresh()
        except (Ipx800v3CannotConnectError, Ipx800v3InvalidAuthError, Ipx800v3RequestError):
            _LOGGER.error("An error occurred while toggle IPX800 light: %s", self.name)
            return None