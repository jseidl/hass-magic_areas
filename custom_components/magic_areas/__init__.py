"""Magic Areas component for Homme Assistant."""

import asyncio
import logging

import voluptuous as vol
from homeassistant.const import EVENT_HOMEASSISTANT_STARTED

from .base import MagicArea
from .const import (
    _DOMAIN_SCHEMA,
    DOMAIN,
    EVENT_MAGICAREAS_AREA_READY,
    EVENT_MAGICAREAS_READY,
    MAGIC_AREAS_COMPONENTS,
    MODULE_DATA,
)

_LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = vol.Schema(
    {DOMAIN: _DOMAIN_SCHEMA},
    extra=vol.ALLOW_EXTRA,
)


async def async_setup(hass, config):
    """Set up areas."""

    # Load registries
    area_registry = await hass.helpers.area_registry.async_get_registry()

    # Populate MagicAreas
    magic_areas = []
    areas = area_registry.async_list_areas()

    magic_areas_config = config[DOMAIN]

    for area in areas:

        _LOGGER.debug(f"Creating Magic Area '{area.name}' (#{area.id}).")
        magic_area = MagicArea(
            hass,
            area,
            magic_areas_config,
        )
        magic_areas.append(magic_area)

    hass.data[MODULE_DATA] = magic_areas

    # Checks whenever an area is ready
    hass.bus.async_listen_once(EVENT_MAGICAREAS_AREA_READY, check_all_ready(hass))
    # Load platforms when ready
    hass.bus.async_listen_once(EVENT_MAGICAREAS_READY, load_platforms(hass, config))

    return True


async def check_all_ready(hass) -> bool:

    areas = hass.data[MODULE_DATA]

    for area in areas:
        if not area.initialized:
            return False

    _LOGGER.debug(f"All areas ready.")
    hass.bus.async_fire(EVENT_MAGICAREAS_READY)

    return True


async def load_platforms(hass, config):

    # Load platforms
    for component in MAGIC_AREAS_COMPONENTS:
        _LOGGER.debug(f"Loading platform '{component}'...")
        hass.async_create_task(
            hass.helpers.discovery.async_load_platform(component, DOMAIN, {}, config)
        )
