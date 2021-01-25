"""Magic Areas component for Homme Assistant."""

import asyncio
import logging

import voluptuous as vol
from homeassistant.config_entries import SOURCE_IMPORT, SOURCE_USER, ConfigEntry
from homeassistant.const import CONF_SOURCE, EVENT_HOMEASSISTANT_STARTED
from homeassistant.core import HomeAssistant
from homeassistant.helpers.area_registry import AreaEntry

from .base import MagicArea, MagicMetaArea
from .const import (
    _DOMAIN_SCHEMA,
    AREA_TYPE_META,
    CONF_ID,
    CONF_NAME,
    CONF_TYPE,
    DATA_AREA_OBJECT,
    DATA_UNDO_UPDATE_LISTENER,
    DOMAIN,
    EVENT_MAGICAREAS_AREA_READY,
    EVENT_MAGICAREAS_READY,
    MAGIC_AREAS_COMPONENTS,
    META_AREAS,
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
    areas = list(area_registry.async_list_areas())

    magic_areas_config = config[DOMAIN]

    # Check reserved names
    reserved_ids = [meta_area.lower() for meta_area in META_AREAS]
    for area in areas:
        if area.id in reserved_ids:
            _LOGGER.error(
                f"Area uses reserved name {area.id}. Please rename your area and restart."
            )
            return

    # Add Meta Areas to area list
    for meta_area in META_AREAS:
        areas.append(AreaEntry(name=meta_area, id=meta_area.lower()))

    for area in areas:

        config_entry = {}
        source = SOURCE_USER

        if area.id not in magic_areas_config.keys():
            default_config = {f"{area.id}": {}}
            config_entry = _DOMAIN_SCHEMA(default_config)[area.id]
        else:
            config_entry = magic_areas_config[area.id]
            source = SOURCE_IMPORT

        if area.id in reserved_ids:
            config_entry.update({CONF_TYPE: AREA_TYPE_META})

        config_entry.update(
            {
                CONF_NAME: area.name,
                CONF_ID: area.id,
            }
        )

        hass.async_create_task(
            hass.config_entries.flow.async_init(
                DOMAIN, context={CONF_SOURCE: source}, data=config_entry
            )
        )

    async def async_check_all_ready(event) -> bool:

        if MODULE_DATA not in hass.data.keys():
            return False

        data = hass.data[MODULE_DATA]
        areas = [area_data[DATA_AREA_OBJECT] for area_data in data.values()]

        for area in areas:
            if area.config.get(CONF_TYPE) == AREA_TYPE_META:
                continue
            if not area.initialized:
                _LOGGER.info(f"Area {area.id} not ready")
                return False

        _LOGGER.debug(f"All areas ready.")
        hass.bus.async_fire(EVENT_MAGICAREAS_READY)

        return True

    # Checks whenever an area is ready
    hass.bus.async_listen(EVENT_MAGICAREAS_AREA_READY, async_check_all_ready)

    return True


async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry):
    """Set up the component."""
    data = hass.data.setdefault(MODULE_DATA, {})
    area_id = config_entry.data[CONF_ID]
    area_name = config_entry.data[CONF_NAME]
    meta_ids = [meta_area.lower() for meta_area in META_AREAS]

    if area_id not in meta_ids:
        area_registry = await hass.helpers.area_registry.async_get_registry()
        area = area_registry.async_get_area(area_id)

        magic_area = MagicArea(
            hass,
            area,
            config_entry,
        )
    else:
        _LOGGER.warn(f"___>>>>>>>> HERE")
        magic_area = MagicMetaArea(hass, area_name, config_entry)

    _LOGGER.debug(f"AREA {area_id} {area_name}: {config_entry.data}")

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
