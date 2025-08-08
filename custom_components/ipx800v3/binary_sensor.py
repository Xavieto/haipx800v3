"""Support for IPX800 V3 binary sensors."""
import logging

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import IpxEntity
from .const import (
    CONF_DEVICES,
    CONF_TYPE,
    CONTROLLER,
    COORDINATOR,
    DOMAIN,
    GLOBAL_PARALLEL_UPDATES,
    TYPE_DIGITALIN,
)

_LOGGER = logging.getLogger(__name__)
PARALLEL_UPDATES = GLOBAL_PARALLEL_UPDATES


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the IPX800 binary sensors."""
    controller = hass.data[DOMAIN][entry.entry_id][CONTROLLER]
    coordinator = hass.data[DOMAIN][entry.entry_id][COORDINATOR]
    devices = hass.data[DOMAIN][entry.entry_id][CONF_DEVICES]["binary_sensor"]

    entities: list[BinarySensorEntity] = []

    for device in devices:
        if device.get(CONF_TYPE) == TYPE_DIGITALIN:
            entities.append(DigitalInBinarySensor(device, controller, coordinator))

    async_add_entities(entities, True)

class DigitalInBinarySensor(IpxEntity, BinarySensorEntity):
    """Representation of a IPX Digital In."""

    @property
    def is_on(self) -> bool:
        """Return the state."""
        return self.coordinator.data[f"IN{self._id}"] == 1
