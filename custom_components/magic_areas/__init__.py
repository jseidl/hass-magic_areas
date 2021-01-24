"""Magic Areas component for Homme Assistant."""

import asyncio
import logging

import voluptuous as vol

from homeassistant.const import EVENT_HOMEASSISTANT_STARTED
from homeassistant.config_entries import SOURCE_IMPORT, SOURCE_USER, ConfigEntry
from homeassistant.const import CONF_SOURCE
from homeassistant.core import HomeAssistant


from .const import (
    MODULE_DATA,
    CONF_ID,
    CONF_NAME,
    DOMAIN,
    _DOMAIN_SCHEMA,
    MAGIC_AREAS_COMPONENTS,
    EVENT_MAGICAREAS_READY,
    EVENT_MAGICAREAS_AREA_READY,
    DATA_AREA_OBJECT,
    DATA_UNDO_UPDATE_LISTENER,
)

from .base import MagicArea

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

        config_entry = {}
        source = SOURCE_USER

        if area.id not in magic_areas_config.keys():
            default_config = {f"{area.id}": {}}
            config_entry = _DOMAIN_SCHEMA(default_config)[area.id]
        else:
            config_entry = magic_areas_config[area.id]
            source = SOURCE_IMPORT

        config_entry.update({
            CONF_NAME: area.name,
            CONF_ID: area.id,
            })

        hass.async_create_task(
            hass.config_entries.flow.async_init(
                DOMAIN, context={CONF_SOURCE: source}, data=config_entry
            )
        )

    #     _LOGGER.debug(
    #         f"Creating Magic Area '{area.name}' (#{area.id})."
    #     )
    #     magic_area = MagicArea(
    #         hass,
    #         area,
    #         magic_areas_config,
    #     )
    #     magic_areas.append(magic_area)

    # hass.data[MODULE_DATA] = magic_areas

    # # Checks whenever an area is ready
    # hass.bus.async_listen_once(
    #             EVENT_MAGICAREAS_AREA_READY, check_all_ready(hass)
    #         )
    # # Load platforms when ready
    # hass.bus.async_listen_once(
    #             EVENT_MAGICAREAS_READY, load_platforms(hass, config)
    #         )

    return True

async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry):
    """Set up the component."""
    data = hass.data.setdefault(MODULE_DATA, {})

    area_registry = await hass.helpers.area_registry.async_get_registry()

    area = area_registry.async_get_area(config_entry.data[CONF_ID])
    _LOGGER.debug(f"AREA {area.id} {area.name}: {config_entry.data}")
    magic_area = MagicArea(
            hass,
            area,
            config_entry,
        )

    undo_listener = config_entry.add_update_listener(async_update_options)

    data[config_entry.entry_id] = {
        DATA_AREA_OBJECT: magic_area,
        DATA_UNDO_UPDATE_LISTENER: undo_listener,
    }

    return True

async def async_update_options(hass, config_entry: ConfigEntry):
    """Update options."""
    await hass.config_entries.async_reload(config_entry.entry_id)

async def async_unload_entry(hass, config_entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    components_unloaded = []
    for component in MAGIC_AREAS_COMPONENTS:
        unload_ok = await hass.config_entries.async_forward_entry_unload(
            config_entry, component
        )
        components_unloaded.append(unload_ok)

    data = hass.data[MODULE_DATA]
    data[config_entry.entry_id][DATA_UNDO_UPDATE_LISTENER]()

    all_unloaded = all(components_unloaded)

    if all_unloaded:
        data.pop(config_entry.entry_id)

    if not data:
        hass.data.pop(MODULE_DATA)

    return all_unloaded

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