"""Magic Areas component for Home Assistant."""

import asyncio
from collections import defaultdict
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.area_registry import async_get as async_get_ar
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .add_entities_when_ready import add_entities_when_ready
from .base.magic import MagicArea, MagicMetaArea
from .const import (
    CONF_ID,
    CONF_NAME,
    DATA_AREA_OBJECT,
    DATA_UNDO_UPDATE_LISTENER,
    META_AREA_EXTERIOR,
    META_AREA_GLOBAL,
    META_AREA_INTERIOR,
    META_AREAS,
    MODULE_DATA,
)
from .util import get_meta_area_object

_LOGGER = logging.getLogger(__name__)

PLATFORMS = []


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
):
    """Set up the component."""
    data = hass.data.setdefault(MODULE_DATA, {})
    area_id = config_entry.data[CONF_ID]
    area_name = config_entry.data[CONF_NAME]

    _LOGGER.debug("Setting up entry for %s", area_name)

    meta_ids = [meta_area.lower() for meta_area in META_AREAS]

    if area_id not in meta_ids:
        area_registry = async_get_ar(hass)
        area = area_registry.async_get_area(area_id)

        if not area:
            _LOGGER.debug("Could not find %s (%s) on registry", area_name, area_id)
            return False

        _LOGGER.debug("Got area %s from registry: %s", area_name, area)

        magic_area = MagicArea(
            hass,
            area,
            config_entry,
        )
    else:
        meta_area = get_meta_area_object(area_name)
        magic_area = MagicMetaArea(hass, meta_area, config_entry)

    _LOGGER.debug(
        "Magic Area %s (%s) created: %s",
        magic_area.name,
        magic_area.id,
        magic_area.config,
    )

    undo_listener = config_entry.add_update_listener(async_update_options)

    data[config_entry.entry_id] = {
        DATA_AREA_OBJECT: magic_area,
        DATA_UNDO_UPDATE_LISTENER: undo_listener,
    }

    # Setup platforms
    for platform in magic_area.available_platforms():
        _LOGGER.debug("Area %s: Loading platform '%s'", magic_area.name, platform)
        hass.async_create_task(
            hass.config_entries.async_forward_entry_setup(config_entry, platform)
        )
        magic_area.loaded_platforms.append(platform)

    #  Conditional reload of related meta-areas

    # Populate dict with all meta-areas with ID as key
    meta_areas = defaultdict()

    for area in data.values():
        area_obj = area[DATA_AREA_OBJECT]
        if area_obj.is_meta():
            meta_areas[area_obj.id] = area_obj

    # Handle non-meta areas
    if not magic_area.is_meta():
        meta_area_key = (
            META_AREA_EXTERIOR.lower()
            if magic_area.is_exterior()
            else META_AREA_INTERIOR.lower()
        )

        if meta_area_key in meta_areas:
            meta_area_object = meta_areas[meta_area_key]

            if meta_area_object.initialized:
                await hass.config_entries.async_reload(
                    meta_area_object.hass_config.entry_id
                )
    else:
        META_AREA_GLOBAL_ID = META_AREA_GLOBAL.lower()

        if magic_area.id != META_AREA_GLOBAL_ID and META_AREA_GLOBAL_ID in meta_areas:
            if meta_areas[META_AREA_GLOBAL_ID].initialized:
                await hass.config_entries.async_reload(
                    meta_areas[META_AREA_GLOBAL_ID].hass_config.entry_id
                )

    return True


async def async_update_options(hass: HomeAssistant, config_entry: ConfigEntry):
    """Update options."""
    await hass.config_entries.async_reload(config_entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Unload a config entry."""

    platforms_unloaded = []
    data = hass.data[MODULE_DATA]
    area_data = data[config_entry.entry_id]
    area = area_data[DATA_AREA_OBJECT]

    for platform in area.loaded_platforms:
        unload_ok = await hass.config_entries.async_forward_entry_unload(
            config_entry, platform
        )
        platforms_unloaded.append(unload_ok)

    area_data[DATA_UNDO_UPDATE_LISTENER]()

    all_unloaded = all(platforms_unloaded)

    if all_unloaded:
        data.pop(config_entry.entry_id)

    if not data:
        hass.data.pop(MODULE_DATA)

    return all_unloaded
