"""Magic Areas component for Home Assistant."""

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
    area_registry = hass.helpers.area_registry.async_get(hass)

    # Populate MagicAreas
    areas = list(area_registry.async_list_areas())
    _LOGGER.debug(f"Areas from registry: {areas}")

    if DOMAIN not in config.keys():
        _LOGGER.error(f"'magic_areas:' not defined on YAML. Aborting.")
        return

    magic_areas_config = config[DOMAIN]

    # Check reserved names
    reserved_names = [meta_area.lower() for meta_area in META_AREAS]
    for area in areas:
        if area.normalized_name in reserved_names:
            _LOGGER.error(
                f"Area uses reserved name {area.normalized_name}. Please rename your area and restart."
            )
            return

    _LOGGER.debug("Area names are valid (not using reserved names), continuing...")

    # Add Meta Areas to area list
    for meta_area in META_AREAS:
        _LOGGER.debug(f"Appending Meta Area {meta_area} to the list of areas")
        areas.append(
            AreaEntry(
                name=meta_area,
                normalized_name=meta_area.lower(),
                aliases=set(),
                id=meta_area.lower(),
            )
        )

    for area in areas:
        _LOGGER.debug(f"Creating/loading configuration for {area.name}.")
        config_entry = {}
        source = SOURCE_USER

        if area.id not in magic_areas_config.keys():
            default_config = {f"{area.id}": {}}
            config_entry = _DOMAIN_SCHEMA(default_config)[area.id]
            _LOGGER.debug(
                f"Configuration for area {area.name} not found on YAML, creating from default."
            )
        else:
            config_entry = magic_areas_config[area.id]
            source = SOURCE_IMPORT
            _LOGGER.debug(
                f"Configuration for area {area.name} found on YAML, loading from saved config."
            )

        if area.normalized_name in reserved_names:
            _LOGGER.debug(f"Meta area {area.name} found, setting correct type.")
            config_entry.update({CONF_TYPE: AREA_TYPE_META})

        extra_opts = {
            CONF_NAME: area.name,
            CONF_ID: area.id,
        }
        config_entry.update(extra_opts)
        _LOGGER.debug(
            f"Configuration for area {area.name} updated with extra options: {extra_opts}"
        )

        _LOGGER.debug(
            f"Creating config flow task for area {area.name} ({area.id}): {config_entry}"
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
                _LOGGER.info(f"Area {area.name} not ready")
                return False

        _LOGGER.debug(f"All areas ready. Firing EVENT_MAGICAREAS_READY.")
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

    _LOGGER.debug(f"Setting up entry for {area_name}")

    meta_ids = [meta_area.lower() for meta_area in META_AREAS]

    if area_id not in meta_ids:
        area_registry = hass.helpers.area_registry.async_get(hass)
        area = area_registry.async_get_area(area_id)

        if not area:
            _LOGGER.debug(f"Could not find {area_name} ({area_id}) on registry")
            return False

        _LOGGER.debug(f"Got area {area_name} from registry: {area}")

        magic_area = MagicArea(
            hass,
            area,
            config_entry,
        )
    else:
        magic_area = MagicMetaArea(hass, area_name, config_entry)

    _LOGGER.debug(
        f"Magic Area {magic_area.name} ({magic_area.id}) created: {magic_area.config}"
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

    # Check if we need to reload meta entities
    data = hass.data[MODULE_DATA]
    area = data[config_entry.entry_id][DATA_AREA_OBJECT]

    if not area.is_meta():
        meta_ids = []
        _LOGGER.debug(f"Area not meta, reloading meta areas.")
        for entry_id, area_data in data.items():
            area = area_data[DATA_AREA_OBJECT]
            if area.is_meta():
                meta_ids.append(entry_id)

        for entry_id in meta_ids:
            await hass.config_entries.async_reload(entry_id)
        _LOGGER.debug(f"Meta areas reloaded.")


async def async_unload_entry(hass, config_entry: ConfigEntry) -> bool:
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
