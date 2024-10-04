from .const import (
    CONF_COMPONENT,
)

def filter_entities_by_platform(devices: list, component: str) -> list:
    """Filter device list by platform."""
    return list(filter(lambda d: d[CONF_COMPONENT] == component, devices))