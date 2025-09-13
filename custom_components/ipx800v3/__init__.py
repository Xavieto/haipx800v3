"""Support for the GCE IPX800 V3."""
from base64 import b64decode
from datetime import timedelta
from http import HTTPStatus
import logging

from aiohttp import web
from pyipx800v3_async import IPX800V3, Ipx800v3CannotConnectError, Ipx800v3InvalidAuthError, Ipx800v3RequestError
import voluptuous as vol

from homeassistant.components.http import HomeAssistantView
from homeassistant.config_entries import SOURCE_IMPORT, ConfigEntry
from homeassistant.const import (
    CONF_DEVICE_CLASS,
    CONF_HOST,
    CONF_ICON,
    CONF_NAME,
    CONF_PASSWORD,
    CONF_PORT,
    CONF_SCAN_INTERVAL,
    CONF_UNIT_OF_MEASUREMENT,
    CONF_USERNAME
)
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.aiohttp_client import async_get_clientsession
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.debounce import Debouncer
from homeassistant.helpers.typing import ConfigType
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
    UpdateFailed,
)
from homeassistant.util import slugify

from .const import (
    CONF_COMPONENT,
    CONF_COMPONENT_ALLOWED,
    CONF_DEFAULT_BRIGHTNESS,
    CONF_DEVICES,
    CONF_ID,
    CONF_UNIQUE_ID,
    CONF_PUSH_PASSWORD,
    CONF_TRANSITION,
    CONF_TYPE,
    CONF_TYPE_ALLOWED,
    CONTROLLER,
    COORDINATOR,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_TRANSITION,
    DOMAIN,
    PLATFORMS,
    PUSH_USERNAME,
    REQUEST_REFRESH_DELAY,
    TYPE_DIGITALIN,
    TYPE_RELAY,
    TYPE_ANALOGIN,
    UNDO_UPDATE_LISTENER,
)

from .tools_entities import (
    filter_entities_by_platform,
)

_LOGGER = logging.getLogger(__name__)

DEVICE_CONFIG_SCHEMA_ENTRY = vol.Schema(
    {
        vol.Required(CONF_NAME): cv.string,
        vol.Required(CONF_UNIQUE_ID): cv.string,
        vol.Required(CONF_COMPONENT): cv.string,
        vol.Required(CONF_TYPE): cv.string,
        vol.Optional(CONF_ID): cv.positive_int,
        vol.Optional(CONF_DEFAULT_BRIGHTNESS): cv.positive_int,
        vol.Optional(CONF_ICON): cv.icon,
        vol.Optional(CONF_TRANSITION, default=DEFAULT_TRANSITION): vol.Coerce(float),
        vol.Optional(CONF_DEVICE_CLASS): cv.string,
        vol.Optional(CONF_UNIT_OF_MEASUREMENT): cv.string,
    }
)

GATEWAY_CONFIG = vol.Schema(
    {
        vol.Required(CONF_NAME): cv.string,
        vol.Required(CONF_HOST): cv.string,
        vol.Optional(CONF_PORT, default=80): cv.port,
        vol.Optional(CONF_USERNAME): cv.string,
        vol.Optional(CONF_PASSWORD): cv.string,
        vol.Optional(CONF_SCAN_INTERVAL): cv.positive_int,
        vol.Optional(CONF_DEVICES, default=[]): vol.All(
            cv.ensure_list, [DEVICE_CONFIG_SCHEMA_ENTRY]
        ),
    },
    extra=vol.ALLOW_EXTRA,
)

CONFIG_SCHEMA = vol.Schema(
    {DOMAIN: vol.All(cv.ensure_list, [GATEWAY_CONFIG])},
    extra=vol.ALLOW_EXTRA,
)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the IPX800 from config file."""
    hass.data.setdefault(DOMAIN, {})

    if DOMAIN in config:
        for gateway in config[DOMAIN]:
            hass.async_create_task(
                hass.config_entries.flow.async_init(
                    DOMAIN, context={"source": SOURCE_IMPORT}, data=gateway
                )
            )

    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up the IPX800v4."""
    hass.data.setdefault(DOMAIN, {})

    config = entry.data
    options = entry.options

    ipx = IPX800V3(
        host=config[CONF_HOST],
        port=config[CONF_PORT],
        username=config[CONF_USERNAME],
        password=config[CONF_PASSWORD]
    )

    try:
        if not await ipx.ping():
            raise Ipx800v3CannotConnectError()
    except Ipx800v3CannotConnectError as exception:
        _LOGGER.error(
            "Cannot connect to the IPX800 named %s, check host, port",
            config[CONF_NAME],
        )
        raise ConfigEntryNotReady from exception
    except Ipx800v3InvalidAuthError as exception:
        _LOGGER.error(
            "Cannot connect to the IPX800 named %s, check username or password",
            config[CONF_NAME],
        )
        raise ConfigEntryNotReady from exception
    except Ipx800v3RequestError as exception:
        _LOGGER.error(
            "Request to IPX800 named %s name failed",
            config[CONF_NAME],
        )
        raise ConfigEntryNotReady from exception

    async def async_update_data():
        """Fetch data from API."""
        try:
            return await ipx.global_get()
        except Ipx800v3CannotConnectError as exception:
            _LOGGER.error(
                "Cannot connect to the IPX800 named %s, check host, port",
                config[CONF_NAME],
            )
            raise ConfigEntryNotReady from exception
        except Ipx800v3InvalidAuthError as exception:
            _LOGGER.error(
                "Cannot connect to the IPX800 named %s, check username or password",
                config[CONF_NAME],
            )
            raise ConfigEntryNotReady from exception
        except Ipx800v3RequestError as exception:
            _LOGGER.error(
                "Request to IPX800 named %s name failed",
                config[CONF_NAME],
            )
            raise ConfigEntryNotReady from exception
        

    scan_interval = options.get(
        CONF_SCAN_INTERVAL, config.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
    )

    if scan_interval < 10:
        _LOGGER.warning(
            "A scan interval too low has been set, you probably will get errors since the IPX800 can't handle too much request at the same time"
        )

    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name=DOMAIN,
        update_method=async_update_data,
        update_interval=timedelta(seconds=scan_interval),
        request_refresh_debouncer=Debouncer(
            hass,
            _LOGGER,
            cooldown=REQUEST_REFRESH_DELAY,
            immediate=False,
        ),
    )

    undo_listener = entry.add_update_listener(_async_update_listener)

    await coordinator.async_refresh()

    hass.data[DOMAIN][entry.entry_id] = {
        CONF_NAME: config[CONF_NAME],
        CONTROLLER: ipx,
        COORDINATOR: coordinator,
        CONF_DEVICES: {},
        UNDO_UPDATE_LISTENER: undo_listener,
    }

    # Create the IPX800 device
    device_registry = dr.async_get(hass)
    device_registry.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, ipx.host)},
        manufacturer="GCE",
        model="IPX800 V3",
        name=config[CONF_NAME],
        configuration_url=f"http://{config[CONF_HOST]}:{config[CONF_PORT]}",
    )

    if CONF_DEVICES not in config:
        _LOGGER.warning(
            "No devices configuration found for the IPX800 %s", config[CONF_NAME]
        )
        return True

    entities = list(config[CONF_DEVICES])

    for platform in PLATFORMS:
        _LOGGER.debug("Load platform %s", platform)
        hass.data[DOMAIN][entry.entry_id][CONF_DEVICES][platform] = (
            filter_entities_by_platform(entities, platform)
        )
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Provide endpoints for the IPX to call to push states
    if CONF_PUSH_PASSWORD in config:
        hass.http.register_view(
            IpxRequestView(config[CONF_HOST], config[CONF_PUSH_PASSWORD])
        )
        hass.http.register_view(
            IpxRequestDataView(config[CONF_HOST], config[CONF_PUSH_PASSWORD])
        )
        hass.http.register_view(
            IpxRequestRefreshView(
                config[CONF_HOST], config[CONF_PUSH_PASSWORD], coordinator
            )
        )
    else:
        _LOGGER.info(
            "No %s parameter provided in configuration, skip API call handling for IPX800 PUSH",
            CONF_PUSH_PASSWORD,
        )

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    for component in CONF_COMPONENT_ALLOWED:
        await hass.config_entries.async_forward_entry_unload(entry, component)

    del hass.data[DOMAIN]

    return True


async def _async_update_listener(hass: HomeAssistant, config_entry: ConfigEntry):
    """Handle options update."""
    await hass.config_entries.async_reload(config_entry.entry_id)


def build_device_list(devices_config: list) -> list:
    """Check and build device list from config."""
    _LOGGER.debug("Check and build devices configuration")

    devices = []
    for device_config in devices_config:
        _LOGGER.debug("Read device name: %s", device_config.get(CONF_NAME))

        # Check if component is supported
        if device_config[CONF_COMPONENT] not in CONF_COMPONENT_ALLOWED:
            _LOGGER.error(
                "Device %s skipped: %s %s not correct or supported",
                device_config[CONF_NAME],
                CONF_COMPONENT,
                device_config[CONF_COMPONENT],
            )
            continue

        # Check if type is supported
        if device_config[CONF_TYPE] not in CONF_TYPE_ALLOWED:
            _LOGGER.error(
                "Device %s skipped: %s %s not correct or supported",
                device_config[CONF_NAME],
                CONF_TYPE,
                device_config[CONF_TYPE],
            )
            continue

        devices.append(device_config)
        _LOGGER.info(
            "Device %s added (component: %s)",
            device_config[CONF_NAME],
            device_config[CONF_COMPONENT],
        )
    return devices


def filter_device_list(devices: list, component: str) -> list:
    """Filter device list by component."""
    return list(filter(lambda d: d[CONF_COMPONENT] == component, devices))


def check_api_auth(request, host, password) -> bool:
    """Check authentication on API call."""
    #if request.remote != host:
    #    _LOGGER.warning("API call not coming from IPX800 IP")
    #    return False
    if "Authorization" not in request.headers:
        _LOGGER.warning("API call no authentication provided")
        return False
    header_auth = request.headers["Authorization"]
    split = header_auth.strip().split(" ")
    if len(split) != 2 or split[0].strip().lower() != "basic":
        _LOGGER.warning("Malformed Authorization header")
        return False
    header_username, header_password = b64decode(split[1]).decode().split(":", 1)
    if header_username != PUSH_USERNAME or header_password != password:
        _LOGGER.warning("API call authentication invalid")
        return False
    return True


class IpxRequestView(HomeAssistantView):
    """Provide a page for the device to call."""

    requires_auth = False
    url = "/api/ipx800v3/{entity_id}/{state}"
    name = "api:ipx800v3"

    def __init__(self, host: str, password: str) -> None:
        """Init the IPX view."""
        self.host = host
        self.password = password
        super().__init__()

    async def get(self, request, entity_id, state):
        """Respond to requests from the device."""
        if not check_api_auth(request, self.host, self.password):
            return web.Response(status=HTTPStatus.UNAUTHORIZED, text="Unauthorized")
        hass = request.app["hass"]
        old_state = hass.states.get(entity_id)
        _LOGGER.debug("Update %s to state %s", entity_id, state)
        if old_state:
            hass.states.async_set(entity_id, state, old_state.attributes)
            return web.Response(status=HTTPStatus.OK, text="OK")
        _LOGGER.warning("Entity not found for state updating: %s", entity_id)


class IpxRequestDataView(HomeAssistantView):
    """Provide a page for the device to call for send multiple data at once."""

    requires_auth = False
    url = "/api/ipx800v3_data/{data}"
    name = "api:ipx800v3_data"

    def __init__(self, host: str, password: str) -> None:
        """Init the IPX view."""
        self.host = host
        self.password = password
        super().__init__()

    async def get(self, request, data):
        """Respond to requests from the device."""
        if not check_api_auth(request, self.host, self.password):
            return web.Response(status=HTTPStatus.UNAUTHORIZED, text="Unauthorized")
        hass = request.app["hass"]
        entities_data = data.split("&")
        for entity_data in entities_data:
            entity_id = entity_data.split("=")[0]
            state = "on" if entity_data.split("=")[1] in ["1", "on", "true"] else "off"

            old_state = hass.states.get(entity_id)
            _LOGGER.debug("Update %s to state %s", entity_id, state)
            if old_state:
                hass.states.async_set(entity_id, state, old_state.attributes)
            else:
                _LOGGER.warning("Entity not found for state updating: %s", entity_id)

        return web.Response(status=HTTPStatus.OK, text="OK")


class IpxRequestRefreshView(HomeAssistantView):
    """Provide a page for the device to force refresh data from coordinator."""

    requires_auth = False
    url = "/api/ipx800v3_refresh/{data}"
    name = "api:ipx800v3_refresh"

    def __init__(
        self, host: str, password: str, coordinator: DataUpdateCoordinator
    ) -> None:
        """Init the IPX view."""
        self.host = host
        self.password = password
        self.coordinator = coordinator
        super().__init__()

    async def get(self, request, data):
        """Respond to requests from the device."""
        if not check_api_auth(request, self.host, self.password):
            return web.Response(status=HTTPStatus.UNAUTHORIZED, text="Unauthorized")
        await self.coordinator.async_request_refresh()
        return web.Response(status=HTTPStatus.OK, text="OK")


class IpxEntity(CoordinatorEntity):
    """Representation of a IPX800 generic device entity."""

    def __init__(
        self,
        device_config: dict,
        ipx: IPX800V3,
        coordinator: DataUpdateCoordinator,
        suffix_name: str = "",
    ) -> None:
        """Initialize the device."""
        super().__init__(coordinator)

        self.ipx = ipx
        self._transition = int(
            device_config.get(CONF_TRANSITION, DEFAULT_TRANSITION) * 1000
        )
        self._ipx_type = device_config[CONF_TYPE]
        self._component = device_config[CONF_COMPONENT]
        self._id = device_config.get(CONF_ID)

        self._attr_name: str = device_config[CONF_NAME]
        self._attr_unique_id: str = device_config[CONF_UNIQUE_ID]
        if suffix_name:
            self._attr_name = f"{self._attr_name} {suffix_name}"
        self._attr_device_class = device_config.get(CONF_DEVICE_CLASS)
        self._attr_native_unit_of_measurement = device_config.get(
            CONF_UNIT_OF_MEASUREMENT
        )
        self._attr_icon = device_config.get(CONF_ICON)
        self._attr_unique_id = "_".join(
            [DOMAIN, self.ipx.host, self._component, slugify(self._attr_name)]
        )

        configuration_url = f"http://{self.ipx.host}:{self.ipx.port}/api/xdevices.json"

        self._attr_device_info = {
            "identifiers": {(DOMAIN, slugify(device_config[CONF_NAME]))},
            "name": device_config[CONF_NAME],
            "manufacturer": "GCE",
            "model": "IPX800 V3",
            "via_device": (DOMAIN, self.ipx.host),
            "configuration_url": configuration_url,
        }
